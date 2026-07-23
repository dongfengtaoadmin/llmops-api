#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将 Markdown 内容转换成 PPTX 并上传到腾讯云 COS。"""

import html
import io
import ipaddress
import logging
import os
import re
import socket
import tempfile
import textwrap
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, List, Optional, Type
from urllib.parse import urlparse

import mistune
import requests
from langchain_core.tools import BaseTool, ToolException
from PIL import Image
from pptx import Presentation, presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Length, Pt
from pydantic import BaseModel, Field

from internal.lib.helper import add_attribute


LOGGER = logging.getLogger(__name__)

MAX_MARKDOWN_LENGTH = 100_000
MAX_SLIDE_COUNT = 60
MAX_BLOCK_COUNT = 600
MAX_IMAGE_COUNT = 10
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 30 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_PPTX_BYTES = 50 * 1024 * 1024
PPTX_DOWNLOAD_URL_TTL = 3600
IMAGE_CONNECT_TIMEOUT = 3
IMAGE_READ_TIMEOUT = 5
IMAGE_TOTAL_TIMEOUT = 12
DEFAULT_IMAGE_ALLOWED_HOSTS = {"placehold.co"}
BASE_CHARS_PER_LINE = 30

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_HTML_IMAGE_PATTERN = re.compile(r"<img\b[^>]*>", flags=re.IGNORECASE)
_HTML_ATTRIBUTE_PATTERN = re.compile(
    r"(?P<name>[a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    flags=re.DOTALL,
)


def _get_allowed_image_hosts() -> set[str]:
    """返回由平台配置控制的图片域名白名单。"""
    hosts = set(DEFAULT_IMAGE_ALLOWED_HOSTS)
    hosts.update(
        host.strip().lower().rstrip(".")
        for host in os.getenv("PPTX_IMAGE_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    )

    cos_domain = os.getenv("COS_DOMAIN", "")
    if cos_domain:
        parsed_cos_domain = urlparse(
            cos_domain if "://" in cos_domain else f"//{cos_domain}"
        )
        cos_hostname = parsed_cos_domain.hostname
        if cos_hostname:
            hosts.add(cos_hostname.lower().rstrip("."))
    return hosts


def _is_allowed_image_host(hostname: str) -> bool:
    """仅允许默认占位图或平台显式配置的自有图片域名。"""
    normalized_hostname = hostname.lower().rstrip(".")
    return normalized_hostname in _get_allowed_image_hosts()


def _plain_text(value: Any) -> str:
    """将 Mistune 生成的少量 HTML 标签还原成纯文本。"""
    text = "" if value is None else str(value)
    return html.unescape(_HTML_TAG_PATTERN.sub("", text)).strip()


class _ListStructureParser(HTMLParser):
    """按原始顺序提取嵌套 HTML 列表中的文字与缩进层级。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items: List[tuple[int, str]] = []
        self._list_stack: List[dict[str, Any]] = []
        self._item_stack: List[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag in {"ul", "ol"}:
            self._flush_current_item()
            self._list_stack.append({"ordered": tag == "ol", "index": 0})
        elif tag == "li" and self._list_stack:
            list_context = self._list_stack[-1]
            list_context["index"] += 1
            self._item_stack.append({
                "depth": len(self._list_stack) - 1,
                "ordered": list_context["ordered"],
                "index": list_context["index"],
                "parts": [],
            })

    def handle_endtag(self, tag: str) -> None:
        if tag == "li" and self._item_stack:
            self._flush_current_item()
            self._item_stack.pop()
        elif tag in {"ul", "ol"} and self._list_stack:
            self._flush_current_item()
            self._list_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._item_stack:
            self._item_stack[-1]["parts"].append(data)

    def _flush_current_item(self) -> None:
        if not self._item_stack:
            return
        item = self._item_stack[-1]
        item_text = "".join(item["parts"]).strip()
        item["parts"].clear()
        if not item_text:
            return
        prefix = f"{item['index']}. " if item["ordered"] else "• "
        self.items.append((item["depth"], f"{prefix}{item_text}"))


def _validate_remote_image_url(url: str) -> None:
    """限制远程图片协议与目标地址，避免工具被用于访问内网资源。"""
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError("只支持 HTTPS 图片地址")
    if parsed_url.username or parsed_url.password:
        raise ValueError("图片地址不允许携带认证信息")
    if parsed_url.port not in {None, 443}:
        raise ValueError("图片地址不允许使用自定义端口")

    hostname = parsed_url.hostname.lower().rstrip(".")
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None and not literal_ip.is_global:
        raise ValueError("图片地址不允许指向本机或内网")
    if not _is_allowed_image_host(hostname):
        raise ValueError("图片域名不在平台白名单中")

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(hostname, 443)
        }
    except OSError as error:
        raise ValueError("图片域名无法解析") from error

    for address in addresses:
        ip_address = ipaddress.ip_address(address)
        if not ip_address.is_global:
            raise ValueError("图片地址不允许指向本机或内网")


def _download_remote_image(url: str, image_folder: str, max_bytes: int) -> tuple[str, int]:
    """下载受限大小的公网图片，并返回临时文件路径。"""
    _validate_remote_image_url(url)
    download_limit = min(MAX_IMAGE_BYTES, max_bytes)
    if download_limit <= 0:
        raise ValueError("整份 PPT 的图片总大小超过限制")

    started_at = time.monotonic()
    with requests.Session() as session:
        session.trust_env = False
        with session.get(
                url,
                stream=True,
                allow_redirects=False,
                timeout=(IMAGE_CONNECT_TIMEOUT, IMAGE_READ_TIMEOUT),
                headers={"User-Agent": "LLMOps-PPTX/1.0"},
        ) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError("图片地址不允许重定向")

            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if not content_type.startswith("image/"):
                raise ValueError("远程地址返回的不是图片")

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > download_limit:
                raise ValueError("远程图片超过大小限制")

            suffix_map = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/gif": ".gif",
                "image/webp": ".webp",
            }
            suffix = suffix_map.get(content_type, Path(urlparse(url).path).suffix.lower())
            if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                suffix = ".img"

            image_path = os.path.join(image_folder, f"{uuid.uuid4()}{suffix}")
            downloaded_size = 0
            with open(image_path, "wb") as image_file:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if time.monotonic() - started_at > IMAGE_TOTAL_TIMEOUT:
                        raise ValueError("远程图片下载超时")
                    if not chunk:
                        continue
                    downloaded_size += len(chunk)
                    if downloaded_size > download_limit:
                        raise ValueError("远程图片超过大小限制")
                    image_file.write(chunk)

    if downloaded_size == 0:
        raise ValueError("远程图片内容为空")
    return image_path, downloaded_size


class PPTRenderer(mistune.HTMLRenderer):
    """把 Mistune 的渲染事件转换成 python-pptx 页面元素。"""

    prs: presentation.Presentation
    font_name: str
    image_folder: str
    content_left: Length
    content_top: Length
    content_width: Length
    line_height: Length

    def __init__(self, prs: presentation.Presentation, image_folder: str):
        super().__init__()
        self.prs = prs
        self.current_slide = None
        self.current_title = ""
        self.document_title = "演示文稿"
        self.font_name = "微软雅黑"
        self.image_folder = image_folder
        self.content_left = Inches(1)
        self.content_top = Inches(1.5)
        self.content_width = Inches(8.5)
        self.content_bottom = Inches(6)
        self.line_height = Pt(24)
        self.image_count = 0
        self.total_image_bytes = 0
        self.block_count = 0

    def heading(self, text: str, level: int, **attrs: Any) -> str:
        """H1 生成封面，其余级别标题均生成一张内容页。"""
        heading_text = _plain_text(text) or "演示文稿"
        self._consume_block()
        if level == 1:
            self.document_title = heading_text
            slide = self._add_slide(0)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            title.text = heading_text
            title.text_frame.paragraphs[0].font.name = self.font_name
            subtitle.text = "由慕课LLMOps平台生成"
            subtitle.text_frame.paragraphs[0].font.name = self.font_name
            self.current_slide = None
            return ""

        self._create_content_slide(heading_text)
        return ""

    def paragraph(self, text: str) -> str:
        """渲染普通正文段落。"""
        paragraph_text = _plain_text(text)
        if paragraph_text:
            self._consume_block()
            self._ensure_content_slide()
            self._add_text_block(paragraph_text, font_size=18)
        return ""

    def list(self, text: str, ordered: bool, **attrs: Any) -> str:
        """渲染有序或无序列表。"""
        tag = "ol" if ordered else "ul"
        list_html = f"<{tag}>{text}</{tag}>"
        if attrs.get("depth", 0) > 0:
            return list_html

        parser = _ListStructureParser()
        parser.feed(list_html)
        self._ensure_content_slide()
        for depth, item_text in parser.items:
            self._consume_block()
            left_indent = Inches(min(1.6, 0.2 + depth * 0.35))
            self._add_text_block(item_text, font_size=18, left_indent=left_indent)
        return ""

    def image(self, text: str, url: str, title: Optional[str] = None) -> str:
        """下载并插入公网图片；失败时保留文字占位，不中断整份 PPT。"""
        alt_text = _plain_text(text) or "图片"
        self._consume_block()
        self._ensure_content_slide()
        if self.image_count >= MAX_IMAGE_COUNT:
            self._add_text_block(f"[图片数量超过 {MAX_IMAGE_COUNT} 张，已忽略：{alt_text}]", font_size=14)
            return ""

        self.image_count += 1
        try:
            remaining_image_bytes = MAX_TOTAL_IMAGE_BYTES - self.total_image_bytes
            image_path, downloaded_size = _download_remote_image(
                url,
                self.image_folder,
                remaining_image_bytes,
            )
            self.total_image_bytes += downloaded_size

            with Image.open(image_path) as image:
                image_width, image_height = image.size
                if image_width * image_height > MAX_IMAGE_PIXELS:
                    raise ValueError("远程图片像素尺寸超过限制")
                if image.format == "WEBP":
                    converted_path = os.path.join(self.image_folder, f"{uuid.uuid4()}.png")
                    image.save(converted_path, format="PNG")
                    converted_size = os.path.getsize(converted_path)
                    additional_size = max(0, converted_size - downloaded_size)
                    if self.total_image_bytes + additional_size > MAX_TOTAL_IMAGE_BYTES:
                        raise ValueError("整份 PPT 的图片总大小超过限制")
                    self.total_image_bytes += additional_size
                    image_path = converted_path
            ratio = image_width / image_height if image_height else 1
            max_width = Inches(4)
            max_height = Inches(3.6)
            picture_width = max_width
            picture_height = int(picture_width / ratio)
            if picture_height > max_height:
                picture_height = max_height
                picture_width = int(picture_height * ratio)

            self.check_new_slide(picture_height + Inches(0.5))
            picture_left = int((self.prs.slide_width - picture_width) / 2)
            self.current_slide.shapes.add_picture(
                image_path,
                picture_left,
                self.content_top,
                width=picture_width,
                height=picture_height,
            )
            self.content_top += picture_height + Inches(0.5)
        except Exception as error:
            LOGGER.warning("PPT 图片处理失败: %s", error)
            self._add_text_block(f"[图片加载失败：{alt_text}]", font_size=14)
        return ""

    def block_code(self, code: str, info: Optional[str] = None) -> str:
        """渲染代码块。"""
        code_text = str(code).strip()
        if code_text:
            self._consume_block()
            self._ensure_content_slide()
            self._add_text_block(
                code_text,
                font_size=14,
                font_name="Consolas",
                color=RGBColor(0x33, 0x66, 0x99),
                background=RGBColor(0xF3, 0xF6, 0xFA),
            )
        return ""

    def inline_html(self, html_text: str) -> str:
        """兼容模型常用的 ``<img src=\"...\">`` 图片写法。"""
        self._render_html_images(html_text)
        return ""

    def block_html(self, html_text: str) -> str:
        """兼容独占一行的 HTML 图片标签。"""
        self._render_html_images(html_text)
        return ""

    def thematic_break(self) -> str:
        """Markdown 分隔线仅作为结构标识，不向 PPT 添加元素。"""
        return ""

    def _render_html_images(self, html_text: str) -> None:
        for image_tag in _HTML_IMAGE_PATTERN.findall(str(html_text)):
            attributes = {
                match.group("name").lower(): match.group("value")
                for match in _HTML_ATTRIBUTE_PATTERN.finditer(image_tag)
            }
            source = attributes.get("src", "")
            if source:
                self.image(attributes.get("alt", "图片"), source)

    def _consume_block(self) -> None:
        self.block_count += 1
        if self.block_count > MAX_BLOCK_COUNT:
            raise ValueError(f"Markdown 内容块不能超过 {MAX_BLOCK_COUNT} 个")

    def _add_slide(self, layout_index: int):
        if len(self.prs.slides) >= MAX_SLIDE_COUNT:
            raise ValueError(f"PPT 页数不能超过 {MAX_SLIDE_COUNT} 页")
        return self.prs.slides.add_slide(self.prs.slide_layouts[layout_index])

    def _create_content_slide(self, title: str) -> None:
        slide = self._add_slide(5)
        title_shape = slide.shapes.title
        title_shape.left = Inches(1)
        title_shape.top = Inches(0.35)
        title_shape.width = Inches(8.5)
        title_shape.text = title
        title_shape.text_frame.paragraphs[0].font.name = self.font_name
        self.current_slide = slide
        self.current_title = title
        self.content_top = Inches(1.5)

    def _create_continuation_slide(self) -> None:
        self._create_content_slide(self.current_title or "续页")

    def _ensure_content_slide(self) -> None:
        if self.current_slide is None:
            self._create_content_slide(self.document_title)

    def check_new_slide(self, required_height: Length = Inches(0)) -> None:
        """在内容达到课程代码定义的 6 英寸边界前创建同标题续页。"""
        self._ensure_content_slide()
        if self.content_top + required_height <= self.content_bottom:
            return
        self._create_continuation_slide()

    def _add_text_block(
            self,
            text: str,
            font_size: int,
            bold: bool = False,
            font_name: Optional[str] = None,
            color: Optional[RGBColor] = None,
            background: Optional[RGBColor] = None,
            left_indent: Length = Inches(0),
    ) -> None:
        width_ratio = float(self.content_width - left_indent) / float(self.content_width)
        chars_per_line = max(
            12,
            int(BASE_CHARS_PER_LINE * (18 / font_size) * width_ratio),
        )
        visual_lines = self._wrap_visual_lines(text, chars_per_line)
        line_height = int(Pt(font_size * 1.35))
        vertical_padding = int(Pt(font_size * 0.35))
        block_gap = int(Pt(4))

        while visual_lines:
            self._ensure_content_slide()
            available_height = int(self.content_bottom - self.content_top - block_gap)
            max_lines = (available_height - vertical_padding) // line_height
            if max_lines <= 0:
                self._create_continuation_slide()
                continue

            chunk_lines = visual_lines[:max_lines]
            visual_lines = visual_lines[max_lines:]
            chunk_text = "\n".join(chunk_lines)
            text_height = int(line_height * len(chunk_lines) + vertical_padding)
            self._render_text_box(
                chunk_text,
                text_height,
                font_size,
                bold,
                font_name,
                color,
                background,
                left_indent,
            )

            if visual_lines:
                self._create_continuation_slide()

    def _render_text_box(
            self,
            text: str,
            text_height: Length,
            font_size: int,
            bold: bool,
            font_name: Optional[str],
            color: Optional[RGBColor],
            background: Optional[RGBColor],
            left_indent: Length,
    ) -> None:
        text_box = self.current_slide.shapes.add_textbox(
            self.content_left + left_indent,
            self.content_top,
            self.content_width - left_indent,
            text_height,
        )
        if background is not None:
            text_box.fill.solid()
            text_box.fill.fore_color.rgb = background
            text_box.line.fill.background()

        text_frame = text_box.text_frame
        text_frame.word_wrap = True
        text_frame.clear()
        text_frame.margin_top = Pt(2)
        text_frame.margin_bottom = Pt(2)
        text_frame.margin_left = Pt(4)
        text_frame.margin_right = Pt(4)
        paragraph = text_frame.paragraphs[0]
        paragraph.text = text
        paragraph.font.name = font_name or self.font_name
        paragraph.font.size = Pt(font_size)
        paragraph.font.bold = bold
        if color is not None:
            paragraph.font.color.rgb = color
        self.content_top += text_height + Pt(4)

    @staticmethod
    def _wrap_visual_lines(text: str, chars_per_line: int = BASE_CHARS_PER_LINE) -> List[str]:
        visual_lines = []
        for source_line in str(text).splitlines() or [""]:
            wrapped_lines = textwrap.wrap(
                source_line,
                width=chars_per_line,
                expand_tabs=False,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=True,
                break_on_hyphens=False,
            )
            visual_lines.extend(wrapped_lines or [""])
        return visual_lines

    @classmethod
    def estimate_text_height(
            cls,
            text: str,
            font_size: int = 20,
            avg_char_per_line: int = BASE_CHARS_PER_LINE,
    ) -> Length:
        """按字符数估算文本框高度，为自动续页预留空间。"""
        visual_line_count = len(cls._wrap_visual_lines(text, avg_char_per_line))
        line_height = Pt(font_size * 1.2)
        return int((visual_line_count + 0.3) * line_height)


def render_markdown_to_pptx(markdown_text: str) -> bytes:
    """将 Markdown 渲染成可直接保存或上传的 PPTX 字节。"""
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        raise ValueError("Markdown 内容不能为空")
    if len(markdown_text) > MAX_MARKDOWN_LENGTH:
        raise ValueError(f"Markdown 内容不能超过 {MAX_MARKDOWN_LENGTH} 个字符")

    with tempfile.TemporaryDirectory() as temp_dir:
        presentation_document = Presentation()
        renderer = PPTRenderer(presentation_document, temp_dir)
        markdown = mistune.create_markdown(renderer=renderer)
        markdown(markdown_text)

        if len(presentation_document.slides) == 0:
            renderer.heading("演示文稿", 1)

        output = io.BytesIO()
        presentation_document.save(output)
        pptx_bytes = output.getvalue()
        if len(pptx_bytes) > MAX_PPTX_BYTES:
            raise ValueError("生成的 PPT 文件不能超过 50MB")
        return pptx_bytes


def _get_cos_service():
    """延迟获取 COS 服务，避免工具模块导入时产生应用初始化循环。"""
    from app.http.module import injector
    from internal.service import CosService

    return injector.get(CosService)


class MarkdownToPPTXArgsSchema(BaseModel):
    """Markdown 转 PPT 工具输入。"""

    markdown: str = Field(
        description="要生成PPT内容的markdown文档字符串。",
        min_length=1,
        max_length=MAX_MARKDOWN_LENGTH,
    )


class MarkdownToPPTXTool(BaseTool):
    """将 Markdown 转换为 PPTX 并返回 COS 下载地址。"""

    name: str = "markdown_to_pptx"
    description: str = (
        "这是一个可以将markdown文本转换成PPT的工具，传递的参数是markdown对应的文本字符串，"
        "返回的数据是PPT的下载地址。当对话正在确认PPT内容且用户回复“确认”或“确认生成PPT”时，"
        "必须调用本工具；markdown参数必须传入此前确认的完整内容。"
        "远程图片仅支持平台配置的 HTTPS 白名单域名。"
    )
    args_schema: Type[BaseModel] = MarkdownToPPTXArgsSchema

    def _run(self, *args: Any, **kwargs: Any) -> str:
        try:
            pptx_bytes = render_markdown_to_pptx(kwargs.get("markdown", ""))
            filename = f"{uuid.uuid4()}.pptx"
            key = f"builtin-tools/markdown-to-pptx/{filename}"

            with tempfile.TemporaryDirectory() as temp_dir:
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, "wb") as pptx_file:
                    pptx_file.write(pptx_bytes)

                cos_service = _get_cos_service()
                cos_client = cos_service.get_client()
                bucket = cos_service.get_bucket()
                cos_client.upload_file(
                    Bucket=bucket,
                    Key=key,
                    LocalFilePath=filepath,
                    EnableMD5=False,
                    progress_callback=None,
                )

            return cos_client.get_presigned_download_url(
                Bucket=bucket,
                Key=key,
                Expired=PPTX_DOWNLOAD_URL_TTL,
            )
        except Exception as error:
            LOGGER.exception("markdown_to_pptx 生成 PPT 失败")
            raise ToolException("生成 PPT 失败，请检查 Markdown 内容或稍后重试。") from error


@add_attribute("args_schema", MarkdownToPPTXArgsSchema)
def markdown_to_pptx(**kwargs: Any) -> BaseTool:
    """返回 Markdown 转 PPTX 的 LangChain 内置工具。"""
    return MarkdownToPPTXTool()

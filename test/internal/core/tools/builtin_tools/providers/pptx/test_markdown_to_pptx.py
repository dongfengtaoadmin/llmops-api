#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Markdown 转 PPTX 内置工具测试。"""

import importlib
import io
from pathlib import Path

import pytest
from PIL import Image as PILImage
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches, Pt

from internal.core.tools.builtin_tools.providers import BuiltinProviderManager


pptx_module = importlib.import_module(
    "internal.core.tools.builtin_tools.providers.pptx.markdown_to_pptx"
)

SAMPLE_MARKDOWN = """# 2026 年度总结

## 核心成果

今年完成了三个重点项目，并持续提升了服务稳定性。

- 核心接口响应速度提升 40%
- 自动化测试覆盖率提升到 85%

### 示例代码

```python
print("hello pptx")
```
"""


def _get_presentation_text(presentation: Presentation) -> str:
    return "\n".join(
        shape.text
        for slide in presentation.slides
        for shape in slide.shapes
        if hasattr(shape, "text") and shape.text
    )


def test_pptx_provider_is_registered():
    """Provider 管理器应能发现工具、输入参数和图标。"""
    manager = BuiltinProviderManager()
    provider = manager.get_provider("pptx")

    assert provider is not None
    assert provider.get_tool_entity("markdown_to_pptx") is not None
    tool_factory = provider.get_tool("markdown_to_pptx")
    assert tool_factory is not None
    assert "markdown" in tool_factory.args_schema.model_fields
    tool = tool_factory()
    assert isinstance(tool, pptx_module.MarkdownToPPTXTool)
    assert "确认生成PPT" in tool.description
    assert "完整内容" in tool.description
    assert provider.provider_entity.icon == "icon.png"
    assert (
        Path(pptx_module.__file__).parent / "_asset" / provider.provider_entity.icon
    ).is_file()


def test_render_markdown_to_pptx_uses_teacher_layout_and_heading_rules():
    """课程代码中的 4:3 布局、封面副标题和标题分页规则应被保留。"""
    markdown = """# 课程封面

## 第一部分

正文内容

### 示例代码

```python
print("teacher")
```
"""

    presentation = Presentation(io.BytesIO(pptx_module.render_markdown_to_pptx(markdown)))

    assert presentation.slide_width == Inches(10)
    assert presentation.slide_height == Inches(7.5)
    assert len(presentation.slides) == 3
    assert presentation.slides[0].shapes.title.text == "课程封面"
    assert presentation.slides[0].placeholders[1].text == "由慕课LLMOps平台生成"
    assert presentation.slides[1].shapes.title.text == "第一部分"
    assert presentation.slides[2].shapes.title.text == "示例代码"

    body_shape = next(
        shape for shape in presentation.slides[1].shapes if getattr(shape, "text", "") == "正文内容"
    )
    assert body_shape.left == Inches(1)
    assert body_shape.width == Inches(8.5)

    code_shape = next(
        shape for shape in presentation.slides[2].shapes if "print" in getattr(shape, "text", "")
    )
    code_font = code_shape.text_frame.paragraphs[0].font
    assert code_font.name == "Consolas"
    assert code_font.size == Pt(14)


def test_render_markdown_to_pptx_generates_valid_presentation():
    """生成结果必须能被 python-pptx 重新打开且保留核心内容。"""
    pptx_bytes = pptx_module.render_markdown_to_pptx(SAMPLE_MARKDOWN)

    assert pptx_bytes.startswith(b"PK")
    presentation = Presentation(io.BytesIO(pptx_bytes))
    presentation_text = _get_presentation_text(presentation)
    assert len(presentation.slides) >= 2
    assert "2026 年度总结" in presentation_text
    assert "核心成果" in presentation_text
    assert "响应速度提升 40%" in presentation_text
    assert "hello pptx" in presentation_text


def test_render_markdown_to_pptx_creates_continuation_slides():
    """超长内容应自动续页，不能挤出幻灯片边界。"""
    long_markdown = "# 长内容测试\n\n## 明细\n\n" + "\n".join(
        f"- 第 {index} 项：这是用于验证自动续页的内容。" for index in range(1, 61)
    )

    presentation = Presentation(io.BytesIO(pptx_module.render_markdown_to_pptx(long_markdown)))
    presentation_text = _get_presentation_text(presentation)

    assert len(presentation.slides) > 2
    assert "第 1 项" in presentation_text
    assert "第 60 项" in presentation_text
    assert {
        slide.shapes.title.text
        for slide in list(presentation.slides)[1:]
        if slide.shapes.title is not None
    } == {"明细"}


def test_render_markdown_to_pptx_preserves_nested_list_order_and_depth():
    """嵌套列表应保持父子顺序，并为子项增加缩进。"""
    markdown = """# 列表测试

## 层级

- outer1
  - inner1
  - inner2
- outer2
"""

    presentation = Presentation(io.BytesIO(pptx_module.render_markdown_to_pptx(markdown)))
    list_shapes = [
        shape
        for slide in presentation.slides
        for shape in slide.shapes
        if hasattr(shape, "text") and shape.text.startswith("• ")
    ]

    assert [shape.text for shape in list_shapes] == [
        "• outer1",
        "• inner1",
        "• inner2",
        "• outer2",
    ]
    assert list_shapes[1].left > list_shapes[0].left
    assert list_shapes[2].left > list_shapes[3].left


def test_render_markdown_to_pptx_splits_a_single_long_paragraph():
    """单个超长文本块也必须拆页，不能生成超出页面边界的文本框。"""
    long_paragraph = "开头标记" + "这是一段很长的正文内容。" * 500 + "结尾标记"
    markdown = f"# 长段落测试\n\n## 正文\n\n{long_paragraph}"

    presentation = Presentation(io.BytesIO(pptx_module.render_markdown_to_pptx(markdown)))
    presentation_text = _get_presentation_text(presentation)

    assert len(presentation.slides) > 2
    assert "开头标记" in presentation_text
    assert "结尾标记" in presentation_text
    for slide in presentation.slides:
        for shape in slide.shapes:
            assert shape.top + shape.height <= presentation.slide_height


def test_render_markdown_to_pptx_enforces_resource_limits(monkeypatch):
    """页数与内容块上限应在创建过多对象前终止渲染。"""
    too_many_slides = "# 封面\n\n" + "\n\n".join(
        f"## 第 {index} 页" for index in range(1, pptx_module.MAX_SLIDE_COUNT + 1)
    )
    with pytest.raises(ValueError, match="PPT 页数不能超过"):
        pptx_module.render_markdown_to_pptx(too_many_slides)

    monkeypatch.setattr(pptx_module, "MAX_BLOCK_COUNT", 5)
    too_many_blocks = "# 封面\n\n## 正文\n\n" + "\n\n".join(
        f"### 内容块 {index}" for index in range(1, 5)
    )
    with pytest.raises(ValueError, match="Markdown 内容块不能超过"):
        pptx_module.render_markdown_to_pptx(too_many_blocks)


def test_render_markdown_to_pptx_rejects_private_image_without_aborting():
    """内网图片应被拒绝，同时保留占位文字并继续生成 PPT。"""
    markdown = "# 安全测试\n\n## 图片\n\n![内网图片](http://127.0.0.1/private.png)"

    pptx_bytes = pptx_module.render_markdown_to_pptx(markdown)
    presentation = Presentation(io.BytesIO(pptx_bytes))

    assert "图片加载失败：内网图片" in _get_presentation_text(presentation)
    with pytest.raises(ValueError, match="本机或内网"):
        pptx_module._validate_remote_image_url("https://127.0.0.1/private.png")
    with pytest.raises(ValueError, match="白名单"):
        pptx_module._validate_remote_image_url("https://example.com/image.png")


def test_render_markdown_to_pptx_centers_teacher_sized_image(monkeypatch):
    """图片应按课程代码中的 4 英寸宽度居中插入。"""

    def create_test_image(url, image_folder, max_bytes):
        image_path = Path(image_folder) / "test-image.png"
        PILImage.new("RGB", (800, 400), color=(210, 82, 48)).save(image_path)
        return str(image_path), image_path.stat().st_size

    monkeypatch.setattr(pptx_module, "_download_remote_image", create_test_image)
    markdown = "# 图片测试\n\n## 图片页\n\n![示例](https://placehold.co/800x400.png)"

    presentation = Presentation(io.BytesIO(pptx_module.render_markdown_to_pptx(markdown)))
    picture = next(
        shape
        for slide in presentation.slides
        for shape in slide.shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    )

    assert picture.width == Inches(4)
    assert picture.left == (presentation.slide_width - Inches(4)) // 2


def test_render_markdown_to_pptx_limits_failed_image_attempts(monkeypatch):
    """失败图片同样计入尝试次数，避免无限超时请求。"""
    download_calls = []

    def fail_download(*args, **kwargs):
        download_calls.append((args, kwargs))
        raise ValueError("模拟图片下载失败")

    monkeypatch.setattr(pptx_module, "_download_remote_image", fail_download)
    markdown = "# 图片次数测试\n\n## 图片\n\n" + "\n\n".join(
        f"![图片 {index}](https://placehold.co/600x400.png?text={index})"
        for index in range(1, pptx_module.MAX_IMAGE_COUNT + 3)
    )

    presentation = Presentation(io.BytesIO(pptx_module.render_markdown_to_pptx(markdown)))

    assert len(download_calls) == pptx_module.MAX_IMAGE_COUNT
    assert len(presentation.slides) >= 2


def test_markdown_to_pptx_tool_uploads_file_and_returns_url(monkeypatch):
    """工具应上传真实 PPTX 字节，并返回 COS 下载地址。"""

    class FakeCosClient:
        upload_kwargs = None
        uploaded_bytes = None
        presign_kwargs = None

        def upload_file(self, **kwargs):
            self.upload_kwargs = kwargs
            self.uploaded_bytes = Path(kwargs["LocalFilePath"]).read_bytes()

        def get_presigned_download_url(self, **kwargs):
            self.presign_kwargs = kwargs
            return f"https://cos.example.com/{kwargs['Key']}?signature=test"

    class FakeCosService:
        def __init__(self):
            self.client = FakeCosClient()

        def get_client(self):
            return self.client

        @classmethod
        def get_bucket(cls):
            return "test-bucket"

        @classmethod
        def get_file_url(cls, key):
            return f"https://cos.example.com/{key}"

    fake_cos_service = FakeCosService()
    monkeypatch.setattr(pptx_module, "_get_cos_service", lambda: fake_cos_service)

    tool = pptx_module.markdown_to_pptx()
    result = tool._run(markdown=SAMPLE_MARKDOWN)

    assert result.startswith("https://cos.example.com/builtin-tools/markdown-to-pptx/")
    assert result.endswith(".pptx?signature=test")
    assert fake_cos_service.client.upload_kwargs["Bucket"] == "test-bucket"
    assert fake_cos_service.client.upload_kwargs["EnableMD5"] is False
    assert fake_cos_service.client.uploaded_bytes.startswith(b"PK")
    assert fake_cos_service.client.presign_kwargs["Bucket"] == "test-bucket"
    assert fake_cos_service.client.presign_kwargs["Expired"] == pptx_module.PPTX_DOWNLOAD_URL_TTL
    Presentation(io.BytesIO(fake_cos_service.client.uploaded_bytes))

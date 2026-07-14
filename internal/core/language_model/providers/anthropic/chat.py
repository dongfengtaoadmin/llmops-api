#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : chat.py
"""
import base64
import ipaddress
import os
import socket
from typing import Any
from urllib.parse import urlparse

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from internal.core.language_model.entities.model_entity import BaseLanguageModel, ModelFeature


SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


class Chat(ChatAnthropic, BaseLanguageModel):
    """Anthropic协议兼容聊天模型"""

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("api_key", os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"))
        kwargs.setdefault("base_url", os.getenv("ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_API_BASE"))

        # Anthropic协议不支持OpenAI的惩罚参数，前端复用默认参数时需要过滤掉。
        kwargs.pop("presence_penalty", None)
        kwargs.pop("frequency_penalty", None)

        super().__init__(**kwargs)

    def convert_to_human_message(self, query: str, image_urls: list[str] = None) -> HumanMessage:
        """将远程图片转成Anthropic协议兼容的Base64消息。"""
        if not image_urls or ModelFeature.IMAGE_INPUT not in self.features:
            return HumanMessage(content=query)

        return HumanMessage(content=[
            {"type": "text", "text": query},
            *[
                {
                    "type": "image_url",
                    "image_url": {"url": self._convert_image_to_data_url(image_url)},
                }
                for image_url in image_urls
            ],
        ])

    @classmethod
    def _convert_image_to_data_url(cls, image_url: str) -> str:
        """下载公网图片并转换为当前LangChain Anthropic适配器要求的Data URL。"""
        if image_url.startswith("data:image/"):
            return image_url

        parsed_url = urlparse(image_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            raise ValueError("图片地址仅支持HTTP/HTTPS公网URL")

        cls._validate_public_hostname(parsed_url.hostname)

        with httpx.stream("GET", image_url, timeout=10, follow_redirects=False) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if content_type not in SUPPORTED_IMAGE_TYPES:
                raise ValueError(f"不支持的图片类型: {content_type or 'unknown'}")

            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_IMAGE_SIZE:
                raise ValueError("单张图片大小不能超过10MB")

            image_data = bytearray()
            for chunk in response.iter_bytes():
                image_data.extend(chunk)
                if len(image_data) > MAX_IMAGE_SIZE:
                    raise ValueError("单张图片大小不能超过10MB")

        encoded_image = base64.b64encode(image_data).decode("ascii")
        return f"data:{content_type};base64,{encoded_image}"

    @staticmethod
    def _validate_public_hostname(hostname: str) -> None:
        """阻止服务端下载环回、内网及保留地址，避免图片URL造成SSRF。"""
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
        except socket.gaierror as error:
            raise ValueError("图片地址无法解析") from error

        for address in addresses:
            ip_address = ipaddress.ip_address(address)
            if not ip_address.is_global:
                raise ValueError("图片地址不能指向内网或保留地址")

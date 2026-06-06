#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/10/25 14:56
@Author  : thezehui@gmail.com
@File    : github_oauth.py
"""
import os
import urllib.parse

import requests

from internal.exception import FailException
from .oauth import OAuth, OAuthUserInfo


class GithubOAuth(OAuth):
    """GithubOAuth第三方授权认证类"""
    _AUTHORIZE_URL = "https://github.com/login/oauth/authorize"  # 跳转授权接口
    _ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"  # 获取授权令牌接口
    _USER_INFO_URL = "https://api.github.com/user"  # 获取用户信息接口
    _EMAIL_INFO_URL = "https://api.github.com/user/emails"  # 获取用户邮箱接口

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        # 某些网络环境需要依赖系统代理访问 GitHub，这里通过环境变量控制是否信任代理配置。
        self.session.trust_env = os.getenv("GITHUB_OAUTH_TRUST_ENV_PROXY", "true").lower() == "true"
        explicit_proxies = self._get_explicit_proxies()
        if explicit_proxies:
            self.session.proxies.update(explicit_proxies)

    @staticmethod
    def _get_explicit_proxies() -> dict[str, str]:
        """读取 GitHub OAuth 专用代理配置，优先级高于 requests 的 trust_env 自动代理。"""
        shared_proxy = os.getenv("GITHUB_OAUTH_PROXY")
        http_proxy = os.getenv("GITHUB_OAUTH_HTTP_PROXY") or shared_proxy
        https_proxy = os.getenv("GITHUB_OAUTH_HTTPS_PROXY") or shared_proxy

        proxies: dict[str, str] = {}
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy

        return proxies

    @staticmethod
    def _get_proxy_hint() -> str:
        """返回当前代理配置诊断信息，便于快速判断为什么浏览器能访问而后端访问不了。"""
        explicit_proxy_keys = [
            "GITHUB_OAUTH_PROXY",
            "GITHUB_OAUTH_HTTP_PROXY",
            "GITHUB_OAUTH_HTTPS_PROXY",
        ]
        system_proxy_keys = [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ]

        explicit_proxy_set = any(os.getenv(key) for key in explicit_proxy_keys)
        system_proxy_set = any(os.getenv(key) for key in system_proxy_keys)

        if explicit_proxy_set:
            return "已检测到 GitHub OAuth 专用代理配置。"
        if system_proxy_set:
            return "已检测到系统代理环境变量，后端会尝试复用它们。"
        return (
            "当前后端进程没有检测到代理环境变量。"
            "浏览器能访问 GitHub，往往只是浏览器插件或浏览器自身走了代理，"
            "Python 后端进程并不会自动继承这条代理链路。"
        )

    def get_provider(self) -> str:
        return "github"

    def get_authorization_url(self) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",  # 只请求用户的基本信息
        }
        return f"{self._AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code: str) -> str:
        # 1.组装请求数据
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}

        # 2.发起post请求并获取相应的数据
        try:
            resp = self.session.post(
                self._ACCESS_TOKEN_URL,
                data=data,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            resp_json = resp.json()
        except requests.exceptions.Timeout as exc:
            raise FailException(
                "连接 GitHub 超时，请检查当前网络是否可访问 github.com，"
                "如本机依赖代理，请确认已配置代理并将 GITHUB_OAUTH_TRUST_ENV_PROXY=true。"
                f"{self._get_proxy_hint()}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise FailException(f"请求 GitHub Access Token 接口失败: {exc}") from exc

        # 3.提取access_token对应的数据
        access_token = resp_json.get("access_token")
        if not access_token:
            error = resp_json.get("error")
            if error == "bad_verification_code":
                raise FailException("GitHub 授权码无效、已过期或已被使用，请重新发起一次 GitHub 登录")
            raise FailException(f"GitHub OAuth 授权失败: {resp_json}")

        return access_token

    def get_raw_user_info(self, token: str) -> dict:
        # 1.组装请求数据
        headers = {"Authorization": f"token {token}"}

        # 2.发起get请求获取用户数据
        try:
            resp = self.session.get(self._USER_INFO_URL, headers=headers, timeout=30)
            resp.raise_for_status()
            raw_info = resp.json()

            # 3.发起get请求获取用户邮箱
            email_resp = self.session.get(self._EMAIL_INFO_URL, headers=headers, timeout=30)
            email_resp.raise_for_status()
            email_info = email_resp.json()
        except requests.exceptions.Timeout as exc:
            raise FailException(
                "获取 GitHub 用户信息超时，请检查当前网络是否可访问 api.github.com。"
                f"{self._get_proxy_hint()}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise FailException(f"获取 GitHub 用户信息失败: {exc}") from exc

        # 4.提取邮箱数据
        primary_email = next((email for email in email_info if email.get("primary", None)), None)

        return {**raw_info, "email": primary_email.get("email", None)}

    def _transform_user_info(self, raw_info: dict) -> OAuthUserInfo:
        # 1.提取邮箱，如果不存在设置一个默认邮箱
        email = raw_info.get("email")
        if not email:
            email = f"{raw_info.get('id')}+{raw_info.get('login')}@user.no-reply@github.com"

        # 2.组装数据
        return OAuthUserInfo(
            id=str(raw_info.get("id")),
            name=str(raw_info.get("name")),
            email=str(email),
        )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/10/25 22:33
@Author  : thezehui@gmail.com
@File    : jwt_service.py
"""
import os
from dataclasses import dataclass
from typing import Any

import jwt
from injector import inject

from internal.exception import UnauthorizedException

# ⏺ JWT_SECRET_KEY 是用于 JWT（JSON Web Token）令牌签名的密钥。
                                                                                                                       
#   工作流程：                                                                                                               
#   1. 用户登录成功后，服务器用这个密钥生成一个 JWT 令牌发给客户端
#   2. 客户端每次请求带上这个令牌                                                                                            
#   3. 服务器用同一个密钥验证令牌是否合法（是否被篡改）          
                                                                                                                           
#   为什么要随机且保密：                                                                                                     
#   - 如果攻击者知道这个密钥，就可以伪造任意用户的身份                                                                       
#   - 像一把"印章"，只有持有印章的人才能签发有效文件                                                                         
                                                                                                                           
#   在你的项目中：                                                                                                           
#   - 用于用户登录认证（auth_handler.py 中的登录逻辑）                                                                       
#   - Flask-Login 配合 JWT 实现用户身份验证                                                                                  
                                                                                                                           
#   简单理解：就是一把"私钥"，用来证明用户身份令牌是真的。

@inject
@dataclass
class JwtService:
    """jwt服务"""

    @classmethod
    def generate_token(cls, payload: dict[str, Any]) -> str:
        """根据传递的载荷信息生成token信息"""
        secret_key = os.getenv("JWT_SECRET_KEY")
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @classmethod
    def parse_token(cls, token: str) -> dict[str, Any]:
        """解析传入的token信息得到载荷"""
        secret_key = os.getenv("JWT_SECRET_KEY")
        try:
            return jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("授权认证凭证已过期请重新登陆")
        except jwt.InvalidTokenError:
            raise UnauthorizedException("解析token出错，请重新登陆")
        except Exception as e:
            raise UnauthorizedException(str(e))

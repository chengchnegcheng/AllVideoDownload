"""
AVD Web版本 - 认证API路由

提供用户认证相关的API接口
"""

from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login():
    """用户登录"""
    return {"message": "认证功能开发中"}

@router.post("/logout")
async def logout():
    """用户登出"""
    return {"message": "用户已登出"} 
#!/usr/bin/env python3
"""
AVD Web版本 - 后端主入口文件

基于FastAPI的Web服务，提供视频下载、字幕生成等功能的API接口
"""

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
import asyncio
import tracemalloc
import warnings
import json

from src.api.routers import downloads, subtitles, auth, system
from src.core.config import settings
from src.core.database import init_db
from src.core.websocket_manager import websocket_manager
from src.utils.logger import setup_logger

# 启用内存追踪以减少警告
tracemalloc.start()

# 过滤一些无害的警告
warnings.filterwarnings("ignore", message=".*Enable tracemalloc.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="transformers.*")

# 设置日志
setup_logger()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动AVD Web服务...")
    
    # 初始化数据库
    await init_db()
    
    # 创建必要的目录
    os.makedirs(settings.FILES_PATH, exist_ok=True)  # 统一的文件目录
    os.makedirs(settings.DOWNLOAD_PATH, exist_ok=True)  # 向后兼容
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)    # 向后兼容
    os.makedirs(settings.TEMP_PATH, exist_ok=True)
    os.makedirs(settings.MODELS_PATH, exist_ok=True)
    
    logger.info("AVD Web服务启动完成")
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭AVD Web服务...")

app = FastAPI(
    title="AVD - 全能视频下载器 Web版",
    description="功能强大的Web端视频下载工具，支持多平台下载、AI字幕生成和翻译",
    version="2.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(downloads.router, prefix="/api/v1/downloads", tags=["下载"])
app.include_router(subtitles.router, prefix="/api/v1/subtitles", tags=["字幕"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统"])

# 新的统一字幕处理系统已整合持久化功能

# 静态文件服务 - 统一文件访问路径
app.mount("/uploads", StaticFiles(directory=settings.FILES_PATH), name="uploads")
app.mount("/downloads", StaticFiles(directory=settings.FILES_PATH), name="downloads")
app.mount("/files", StaticFiles(directory=settings.FILES_PATH), name="files")  # 新的统一访问路径

@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "AVD Web API 服务运行中",
        "version": "2.0.0",
        "docs_url": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "message": "服务运行正常"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接处理 - 简化版本，确保稳定连接"""
    connection_id = f"conn_{id(websocket)}"
    
    try:
        await websocket_manager.connect(websocket, connection_id)
        logger.info(f"WebSocket连接成功: {connection_id}")
        
        # 发送连接确认消息
        await websocket_manager.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "WebSocket连接成功"
        }, websocket)
        
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    
                    # 处理心跳
                    if message.get('type') == 'ping':
                        await websocket_manager.send_personal_message({
                            "type": "pong",
                            "timestamp": asyncio.get_event_loop().time()
                        }, websocket)
                        continue
                        
                    # 处理其他消息
                    logger.debug(f"收到WebSocket消息: {message}")
                    
                except json.JSONDecodeError:
                    logger.warning(f"无效的WebSocket消息格式: {data}")
                    
            except Exception as e:
                logger.info(f"WebSocket连接断开: {connection_id}, 原因: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket连接已清理: {connection_id}")

if __name__ == "__main__":
    # 配置文件监控排除目录，避免监控日志文件导致无限循环
    reload_dirs = [str(Path(__file__).parent)] if settings.DEBUG else None
    reload_excludes = [
        "logs/*",           # 排除日志目录
        "*.log",           # 排除日志文件
        "data/*",          # 排除数据目录
        "temp/*",          # 排除临时目录
        "*.db",            # 排除数据库文件
        "*.pyc",           # 排除编译文件
        "__pycache__/*",   # 排除缓存目录
    ] if settings.DEBUG else None
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        reload_dirs=reload_dirs,
        reload_excludes=reload_excludes,
        log_level="info",
        timeout_keep_alive=300,  # 保持连接5分钟
        timeout_graceful_shutdown=60,  # 优雅关闭超时1分钟
        limit_max_requests=None,  # 取消最大请求数限制
    ) 
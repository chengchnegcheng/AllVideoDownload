"""
AVD Web版本 - 视频下载器

主要功能：
1. 统一的视频下载接口
2. 支持多平台视频下载 
3. 实时进度追踪和WebSocket推送
4. 流式下载支持
"""

import os
import json
import logging
import asyncio
import subprocess
import tempfile
import re
import time
from typing import Dict, Any, Optional, Callable, List, AsyncGenerator, Union
from dataclasses import dataclass
import aiohttp
import yt_dlp

from .downloaders.downloader_factory import DownloaderFactory
from .downloaders import DownloadOptions
from ..utils.validators import validate_url

logger = logging.getLogger(__name__)

class VideoDownloader:
    """统一视频下载器"""
    
    def __init__(self):
        self.factory = DownloaderFactory()
        self.progress_callbacks: Dict[str, Callable] = {}
        self.download_processes: Dict[str, subprocess.Popen] = {}
    
    def _detect_platform(self, url: str) -> str:
        """检测视频平台
        
        Args:
            url: 视频URL
            
        Returns:
            平台名称
        """
        url_lower = url.lower()
        
        platform_patterns = {
            'youtube': [r'youtube\.com', r'youtu\.be', r'm\.youtube\.com'],
            'bilibili': [r'bilibili\.com', r'b23\.tv'],
            'douyin': [r'douyin\.com', r'iesdouyin\.com'],
            'weixin': [r'weixin\.qq\.com', r'mp\.weixin\.qq\.com'],
            'xiaohongshu': [r'xiaohongshu\.com', r'xhslink\.com'],
            'qq': [r'v\.qq\.com'],
            'youku': [r'youku\.com'],
            'iqiyi': [r'iqiyi\.com', r'iq\.com']
        }
        
        for platform, patterns in platform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return platform
        
        return 'generic'
    
    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """获取视频信息
        
        Args:
            url: 视频URL
            
        Returns:
            视频信息字典
        """
        try:
            if not validate_url(url):
                raise ValueError("无效的URL格式")
            
            # 使用工厂获取下载器
            downloader = self.factory.get_downloader(url)
            logger.info(f"为URL {url} 选择了 {downloader.get_platform_name()} 下载器")
            
            # 获取视频信息
            info = await downloader.get_video_info(url)
            
            if info:
                logger.info(f"成功获取视频信息，平台: {info.get('platform', 'unknown')}")
            
            return info
            
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return None

    async def download(self, url: str, options: DownloadOptions, 
                      progress_callback: Optional[Callable] = None, 
                      task_id: str = None) -> Dict[str, Any]:
        """下载视频
        
        Args:
            url: 视频URL
            options: 下载选项
            progress_callback: 进度回调函数 
            task_id: 任务ID
            
        Returns:
            下载结果字典
        """
        try:
            if not validate_url(url):
                raise ValueError("无效的URL格式")
            
            # 确保输出目录存在
            os.makedirs(options.output_path, exist_ok=True)
            
            # 使用工厂选择合适的下载器
            downloader = self.factory.get_downloader(url)
            logger.info(f"使用 {downloader.get_platform_name()} 下载器处理URL: {url}")
            
            # 调用下载器的下载方法
            result = await downloader.download(url, options, progress_callback, task_id)
            
            if result.get("success"):
                logger.info(f"下载成功: {result.get('file_path', '')}")
            else:
                logger.error(f"下载失败: {result.get('error', '未知错误')}")
            
            return result
                
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": None
            }

    async def cancel_download(self, task_id: str):
        """取消下载任务"""
        try:
            # 移除进度回调
            if task_id in self.progress_callbacks:
                del self.progress_callbacks[task_id]
            
            # 终止进程
            if task_id in self.download_processes:
                process = self.download_processes[task_id]
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                del self.download_processes[task_id]
                
            logger.info(f"已取消下载任务: {task_id}")
            
        except Exception as e:
            logger.error(f"取消下载任务失败: {e}")

    def get_supported_platforms(self) -> List[Dict[str, Any]]:
        """获取所有支持的平台信息"""
        return self.factory.get_supported_platforms()
    
    def test_url_support(self, url: str) -> Dict[str, Any]:
        """测试URL支持情况"""
        return self.factory.test_url_support(url)

    def cleanup(self):
        """清理资源"""
        try:
            # 清理所有回调
            self.progress_callbacks.clear()
            
            # 终止所有进程
            for task_id, process in self.download_processes.items():
                if process and process.poll() is None:
                    try:
                        process.terminate()
                        process.wait(timeout=3)
                    except:
                        try:
                            process.kill()
                        except:
                            pass
            
            self.download_processes.clear()
            
            # 清理下载器工厂资源
            self.factory.cleanup_all()
            
            logger.info("下载器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理下载器资源失败: {e}")

# 全局下载器实例
downloader_instance = VideoDownloader() 
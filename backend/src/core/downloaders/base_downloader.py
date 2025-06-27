"""
基础下载器抽象类

定义所有平台下载器的通用接口和共同功能
"""

import asyncio
import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
import yt_dlp
from urllib.parse import urlparse

try:
    from ..config import settings
    from ...utils.validators import validate_url
    from ...utils.logger import format_error_message
except ImportError:
    # 当从外部运行时的备用导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from core.config import settings
    from utils.validators import validate_url
    from utils.logger import format_error_message

logger = logging.getLogger(__name__)

@dataclass
class DownloadOptions:
    """下载选项配置"""
    quality: str = "best"
    format: str = "mp4"
    audio_only: bool = False
    subtitle: bool = False
    subtitle_language: str = "auto"
    output_filename: Optional[str] = None
    output_path: str = ""
    cookies_file: Optional[str] = None
    proxy: Optional[str] = None

class BaseDownloader(ABC):
    """基础下载器抽象类"""
    
    def __init__(self):
        self.download_processes = {}  # 存储活跃的下载进程
        self.progress_callbacks = {}  # 存储进度回调函数
        self.platform_name = self.get_platform_name()
        self._main_loop = None  # 存储主事件循环
        
    @abstractmethod
    def get_platform_name(self) -> str:
        """获取平台名称"""
        pass
    
    @abstractmethod
    def get_supported_domains(self) -> List[str]:
        """获取支持的域名列表"""
        pass
    
    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL"""
        pass
    
    def get_base_ydl_options(self, options: DownloadOptions, task_id: str = None) -> Dict[str, Any]:
        """获取基础yt-dlp选项"""
        # 根据是否指定了output_filename来构建输出模板
        if options.output_filename:
            # 如果指定了文件名，直接使用
            outtmpl = os.path.join(options.output_path, options.output_filename)
        else:
            # 否则使用视频标题
            outtmpl = os.path.join(options.output_path, "%(title)s.%(ext)s")
        
        ydl_opts = {
            "outtmpl": outtmpl,
            "writeinfojson": True,
            "writesubtitles": options.subtitle,
            "writeautomaticsub": options.subtitle,
            "subtitleslangs": [options.subtitle_language] if options.subtitle_language != "auto" else None,
            "ignoreerrors": False,
            "no_warnings": False,
            # 基础反爬虫配置
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "sleep_interval": 1,
            "max_sleep_interval": 3,
            "extractor_retries": 3,
            "retries": 10,
        }
        
        # 质量和格式设置
        if options.audio_only:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            ydl_opts["format"] = self.get_format_selector(options)
        
        # 代理设置
        proxy_url = options.proxy or settings.HTTP_PROXY
        if proxy_url:
            ydl_opts["proxy"] = proxy_url
        
        # 进度钩子
        if task_id and task_id in self.progress_callbacks:
            ydl_opts["progress_hooks"] = [self._progress_hook(task_id)]
        
        return ydl_opts
    
    @abstractmethod
    def get_platform_specific_options(self, options: DownloadOptions, url: str) -> Dict[str, Any]:
        """获取平台特定的yt-dlp选项"""
        pass
    
    def get_format_selector(self, options: DownloadOptions) -> str:
        """获取格式选择器，子类可以重写以自定义格式选择"""
        if options.quality == "best":
            return f"best[ext={options.format}]/best"
        elif options.quality == "worst":
            return f"worst[ext={options.format}]/worst"
        elif options.quality.endswith("p"):
            height = options.quality[:-1]
            return f"best[height<={height}][ext={options.format}]/best[height<={height}]/best"
        else:
            return f"best[ext={options.format}]/best"
    
    def _progress_hook(self, task_id: str):
        """创建进度钩子函数"""
        def hook(d):
            if task_id not in self.progress_callbacks:
                logger.debug(f"任务 {task_id} 没有进度回调函数")
                return
            
            callback = self.progress_callbacks[task_id]
            logger.debug(f"进度钩子被调用 - 任务ID: {task_id}, 状态: {d.get('status')}")
            
            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                progress = 0
                if total_bytes > 0:
                    progress = (downloaded_bytes / total_bytes) * 100
                
                progress_data = {
                    "status": "downloading",
                    "progress": progress,
                    "total_bytes": total_bytes,
                    "downloaded_bytes": downloaded_bytes,
                    "speed": speed or 0,
                    "eta": eta or 0,
                    "title": d.get('info_dict', {}).get('title', '')
                }
                
                logger.debug(f"发送进度数据: {progress:.1f}%, 速度: {speed}, ETA: {eta}")
                
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # 检查是否有运行中的事件循环
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(callback(progress_data))
                        except RuntimeError:
                            # 没有运行中的事件循环，使用主循环
                            if hasattr(self, '_main_loop') and self._main_loop:
                                asyncio.run_coroutine_threadsafe(callback(progress_data), self._main_loop)
                            else:
                                logger.warning(f"无法发送进度更新，没有可用的事件循环")
                    else:
                        callback(progress_data)
                except Exception as e:
                    logger.error(f"进度回调执行失败: {e}")
            
            elif d['status'] == 'finished':
                progress_data = {
                    "status": "finished",
                    "progress": 100,
                    "filename": d['filename'],
                    "total_bytes": d.get('total_bytes', 0)
                }
                
                try:
                    if asyncio.iscoroutinefunction(callback):
                        # 检查是否有运行中的事件循环
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(callback(progress_data))
                        except RuntimeError:
                            # 没有运行中的事件循环，使用主循环
                            if hasattr(self, '_main_loop') and self._main_loop:
                                asyncio.run_coroutine_threadsafe(callback(progress_data), self._main_loop)
                            else:
                                logger.warning(f"无法发送完成通知，没有可用的事件循环")
                    else:
                        callback(progress_data)
                except Exception as e:
                    logger.error(f"完成回调执行失败: {e}")
        
        return hook
    
    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """获取视频信息"""
        try:
            if not validate_url(url):
                raise ValueError("无效的URL格式")
            
            if not self.supports_url(url):
                raise ValueError(f"该URL不被{self.platform_name}下载器支持")
            
            # 构建yt-dlp选项
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }
            
            # 添加平台特定选项
            platform_opts = self.get_info_options(url)
            ydl_opts.update(platform_opts)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                if not info:
                    return None
                
                return self.process_video_info(info, url)
                
        except Exception as e:
            error_msg = format_error_message(str(e), f"{self.platform_name}获取视频信息失败")
            logger.error(error_msg)
            return None
    
    @abstractmethod
    def get_info_options(self, url: str) -> Dict[str, Any]:
        """获取信息提取时的平台特定选项"""
        pass
    
    def process_video_info(self, info: Dict[str, Any], url: str) -> Dict[str, Any]:
        """处理视频信息，子类可以重写以自定义信息处理"""
        # 提取可用格式和质量
        formats = info.get('formats', [])
        available_qualities = []
        available_formats = []
        
        for fmt in formats:
            if fmt.get('height'):
                quality = f"{fmt['height']}p"
                if quality not in available_qualities:
                    available_qualities.append(quality)
            
            if fmt.get('ext'):
                format_ext = fmt['ext']
                if format_ext not in available_formats:
                    available_formats.append(format_ext)
        
        # 排序质量选项
        quality_order = ['2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p']
        available_qualities = sorted(available_qualities, 
                                   key=lambda x: quality_order.index(x) if x in quality_order else 999)
        
        return {
            "title": info.get("title", "未知标题"),
            "description": info.get("description", ""),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", ""),
            "upload_date": info.get("upload_date", ""),
            "view_count": info.get("view_count", 0),
            "platform": self.platform_name,
            "available_qualities": available_qualities,
            "available_formats": list(set(available_formats)),
            "webpage_url": info.get("webpage_url", url),
            "id": info.get("id", ""),
            "extractor": info.get("extractor", "")
        }
    
    async def download(self, url: str, options: DownloadOptions, 
                      progress_callback: Optional[Callable] = None, 
                      task_id: str = None) -> Dict[str, Any]:
        """下载视频"""
        try:
            if not validate_url(url):
                raise ValueError("无效的URL格式")
            
            if not self.supports_url(url):
                raise ValueError(f"该URL不被{self.platform_name}下载器支持")
            
            # 确保输出目录存在
            os.makedirs(options.output_path, exist_ok=True)
            
            # 注册进度回调
            if progress_callback and task_id:
                self.progress_callbacks[task_id] = progress_callback
                # 保存当前事件循环
                self._main_loop = asyncio.get_running_loop()
            
            # 构建yt-dlp选项
            ydl_opts = self.get_base_ydl_options(options, task_id)
            platform_opts = self.get_platform_specific_options(options, url)
            ydl_opts.update(platform_opts)
            
            # 执行下载
            downloaded_files = []
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 先获取信息以确定文件名
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                if not info:
                    raise Exception("无法获取视频信息")
                
                # 构建预期的文件路径
                filename = ydl.prepare_filename(info)
                
                # 开始下载
                await asyncio.to_thread(ydl.download, [url])
                
                # 检查下载的文件
                if os.path.exists(filename):
                    downloaded_files.append(filename)
                else:
                    # 查找可能的文件名变化
                    base_path = Path(filename).parent
                    base_name = Path(filename).stem
                    
                    for file in base_path.glob(f"{base_name}.*"):
                        if file.is_file():
                            downloaded_files.append(str(file))
                            break
                
                if not downloaded_files:
                    raise Exception("下载完成但找不到文件")
                
                return {
                    "success": True,
                    "file_path": downloaded_files[0],
                    "files": downloaded_files,
                    "title": info.get("title", ""),
                    "message": f"{self.platform_name}下载完成"
                }
                
        except Exception as e:
            error_msg = format_error_message(str(e), f"{self.platform_name}下载失败")
            logger.error(error_msg)
            return {
                "success": False,
                "error": format_error_message(str(e)),  # 返回清理后的错误消息
                "file_path": None
            }
        finally:
            # 清理回调
            if task_id and task_id in self.progress_callbacks:
                del self.progress_callbacks[task_id]
    
    async def cancel_download(self, task_id: str):
        """取消下载任务"""
        try:
            if task_id in self.progress_callbacks:
                del self.progress_callbacks[task_id]
            
            if task_id in self.download_processes:
                process = self.download_processes[task_id]
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except:
                        process.kill()
                del self.download_processes[task_id]
                
            logger.info(f"{self.platform_name}已取消下载任务: {task_id}")
            
        except Exception as e:
            logger.error(f"{self.platform_name}取消下载任务失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            self.progress_callbacks.clear()
            
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
            logger.info(f"{self.platform_name}下载器资源清理完成")
            
        except Exception as e:
            logger.error(f"{self.platform_name}清理下载器资源失败: {e}") 
"""
URL处理器模块

负责从URL下载视频/音频并生成字幕
"""

import os
import glob
import time
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings
from .subtitle_generator import SubtitleGenerator
from .subtitle_translator import SubtitleTranslator


class URLProcessor:
    """URL处理器"""
    
    def __init__(self):
        """初始化URL处理器"""
        self.subtitle_generator = SubtitleGenerator()
        self.subtitle_translator = SubtitleTranslator()
        logger.info("URL处理器初始化完成")
    
    async def generate_subtitles_from_url(self,
                                        url: str,
                                        language: str = "auto",
                                        model_size: str = None,
                                        translate_to: Optional[str] = None,
                                        download_video: bool = True,
                                        progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        从URL生成字幕
        
        Args:
            url: 视频URL
            language: 语言代码
            model_size: 模型大小
            translate_to: 翻译目标语言
            download_video: 是否保留视频文件
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 导入下载器工厂
            from ..downloaders.downloader_factory import downloader_factory
            from ..downloaders import DownloadOptions
            
            if progress_callback:
                await progress_callback(5, "正在分析视频URL...")
            
            # 创建下载器
            downloader = downloader_factory.get_downloader(url)
            if not downloader:
                raise Exception("不支持的视频平台")
            
            # 获取视频信息
            video_info = await downloader.get_video_info(url)
            if not video_info:
                raise Exception("无法获取视频信息")
                
            video_title = video_info.get("title", "unknown_video")
            safe_title = self._sanitize_filename(video_title)
            
            if progress_callback:
                await progress_callback(10, f"正在下载音频: {video_title}")
            
            # 设置下载选项 - 只下载音频，提高效率
            download_options = DownloadOptions(
                audio_only=True, 
                output_path=settings.TEMP_PATH,
                output_filename=f"{safe_title}_audio.%(ext)s"
            )
            
            # 下载音频文件
            download_result = await downloader.download(url, download_options)
            
            if not download_result["success"]:
                raise Exception(f"音频下载失败: {download_result.get('error', '未知错误')}")
            
            downloaded_file = download_result["file_path"]
            
            # 智能查找实际的音频文件
            actual_audio_file = await self._find_actual_audio_file(downloaded_file, safe_title)
            
            if not actual_audio_file or not os.path.exists(actual_audio_file):
                raise Exception(f"无法找到下载的音频文件")
            
            logger.info(f"找到实际音频文件: {actual_audio_file}")
            
            if progress_callback:
                await progress_callback(30, "音频下载完成，开始生成字幕...")
            
            # 创建字幕生成的进度回调
            async def subtitle_progress(progress, message=""):
                # 将进度映射到 30-90 的范围
                total_progress = 30 + (progress * 0.6)
                if progress_callback:
                    await progress_callback(total_progress, message)
            
            # 生成字幕
            result = await self.subtitle_generator.generate_from_audio(
                actual_audio_file,
                language=language,
                model_size=model_size,
                progress_callback=subtitle_progress,
                audio_title=video_title
            )
            
            if not result["success"]:
                return result
            
            # 如果需要翻译
            if translate_to:
                if progress_callback:
                    await progress_callback(90, "正在翻译字幕...")
                
                translate_result = await self.subtitle_translator.translate_subtitles(
                    result["subtitle_file"],
                    target_language=translate_to
                )
                
                if translate_result["success"]:
                    result["subtitle_file"] = translate_result["translated_file"]
                    result["translated"] = True
            
            if progress_callback:
                await progress_callback(100, "处理完成")
            
            # 清理临时文件
            await self._cleanup_temp_files(actual_audio_file, downloaded_file, keep_video=download_video)
            
            result["video_file"] = actual_audio_file if download_video else None
            result["source_url"] = url
            result["source_type"] = "url"
            
            return result
            
        except Exception as e:
            logger.error(f"从URL生成字幕失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _find_actual_audio_file(self, downloaded_file: str, safe_title: str) -> str:
        """
        智能查找实际的音频文件
        
        Args:
            downloaded_file: 下载器返回的文件路径
            safe_title: 安全的标题名称
            
        Returns:
            str: 实际的音频文件路径
        """
        try:
            # 如果下载的就是音频文件，直接返回
            if downloaded_file and os.path.exists(downloaded_file):
                # 检查文件扩展名
                ext = os.path.splitext(downloaded_file)[1].lower()
                if ext in ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.webm', '.mp4']:
                    return downloaded_file
            
            # 如果返回的是.info.json文件，查找对应的音频文件
            if downloaded_file and downloaded_file.endswith('.info.json'):
                base_name = downloaded_file.replace('.info.json', '')
                
                # 查找可能的音频文件扩展名
                audio_extensions = ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.webm', '.mp4']
                for ext in audio_extensions:
                    possible_file = base_name + ext
                    if os.path.exists(possible_file):
                        return possible_file
            
            # 按文件名模式查找
            temp_dir = settings.TEMP_PATH
            audio_extensions = ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.webm', '.mp4']
            
            # 查找包含标题的音频文件
            for ext in audio_extensions:
                # 精确匹配
                pattern1 = os.path.join(temp_dir, f"{safe_title}_audio{ext}")
                if os.path.exists(pattern1):
                    return pattern1
                
                # 模糊匹配
                pattern2 = os.path.join(temp_dir, f"*{safe_title}*{ext}")
                matches = glob.glob(pattern2)
                if matches:
                    # 返回最新的文件
                    return max(matches, key=os.path.getctime)
            
            # 查找最新创建的音频文件
            audio_files = []
            for ext in audio_extensions:
                pattern = os.path.join(temp_dir, f"*{ext}")
                audio_files.extend(glob.glob(pattern))
            
            if audio_files:
                # 返回最新创建的音频文件
                newest_file = max(audio_files, key=os.path.getctime)
                # 确保文件是最近5分钟内创建的
                if time.time() - os.path.getctime(newest_file) < 300:  # 5分钟
                    return newest_file
            
            return None
            
        except Exception as e:
            logger.error(f"查找音频文件失败: {e}")
            return None
    
    async def _cleanup_temp_files(self, audio_file: str, downloaded_file: str, keep_video: bool = False):
        """
        清理临时文件
        
        Args:
            audio_file: 音频文件路径
            downloaded_file: 下载的文件路径
            keep_video: 是否保留视频文件
        """
        try:
            files_to_clean = []
            
            if not keep_video:
                # 添加音频文件到清理列表
                if audio_file and os.path.exists(audio_file):
                    files_to_clean.append(audio_file)
                
                # 添加下载的原始文件（如果不同于音频文件）
                if downloaded_file and downloaded_file != audio_file and os.path.exists(downloaded_file):
                    files_to_clean.append(downloaded_file)
                
                # 清理相关的.info.json文件
                if audio_file:
                    info_file = os.path.splitext(audio_file)[0] + '.info.json'
                    if os.path.exists(info_file):
                        files_to_clean.append(info_file)
            
            # 执行清理
            for file_path in files_to_clean:
                try:
                    os.remove(file_path)
                    logger.info(f"已清理临时文件: {file_path}")
                except Exception as e:
                    logger.warning(f"清理文件失败 {file_path}: {e}")
                    
        except Exception as e:
            logger.warning(f"清理临时文件过程出错: {e}")
    
    def _sanitize_filename(self, filename: str, max_length: int = 200, default_name: str = "video") -> str:
        """
        清理文件名，移除特殊字符
        
        Args:
            filename: 原始文件名
            max_length: 最大长度
            default_name: 默认名称
            
        Returns:
            str: 清理后的文件名
        """
        if not filename:
            return default_name
        
        import re
        
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # 移除表情符号和其他Unicode特殊字符
        filename = re.sub(r'[^\w\s\-_\.]', '_', filename)
        
        # 移除多余的空格、下划线和点
        filename = re.sub(r'[_\s]+', '_', filename).strip('_.')
        
        # 确保不以点开头或结尾
        filename = filename.strip('.')
        
        # 限制长度
        if len(filename.encode('utf-8')) > max_length:
            result_name = ""
            for char in filename:
                test_result = result_name + char
                if len(test_result.encode('utf-8')) > max_length:
                    break
                result_name = test_result
            filename = result_name.strip()
            if not filename:
                filename = default_name
        
        return filename if filename else default_name
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        获取视频信息
        
        Args:
            url: 视频URL
            
        Returns:
            Dict[str, Any]: 视频信息
        """
        try:
            # 导入下载器工厂
            from ..downloaders.downloader_factory import downloader_factory
            
            # 创建下载器
            downloader = downloader_factory.get_downloader(url)
            if not downloader:
                return {
                    "success": False,
                    "error": "不支持的视频平台"
                }
            
            # 获取视频信息
            video_info = await downloader.get_video_info(url)
            if not video_info:
                return {
                    "success": False,
                    "error": "无法获取视频信息"
                }
            
            return {
                "success": True,
                "info": video_info
            }
            
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        try:
            from ..downloaders.downloader_factory import downloader_factory
            return downloader_factory.get_supported_platforms()
        except Exception as e:
            logger.error(f"获取支持平台列表失败: {e}")
            return ["YouTube", "Bilibili"]  # 默认支持的平台 
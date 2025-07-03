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


import asyncio
import traceback

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
        从URL生成字幕 - 增强错误处理版本
        
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
                error_msg = "不支持的视频平台"
                logger.error(f"URLProcessor错误: {error_msg}")
                if progress_callback:
                    await progress_callback(0, f"错误: {error_msg}")
                return {"success": False, "error": error_msg}
            
            # 获取视频信息 - 增加重试机制
            video_info = None
            for attempt in range(3):  # 重试3次
                try:
                    if progress_callback:
                        await progress_callback(8 + attempt * 2, f"正在获取视频信息(尝试 {attempt + 1}/3)...")
                    
                    video_info = await downloader.get_video_info(url)
                    if video_info:
                        break
                        
                except Exception as e:
                    logger.warning(f"获取视频信息失败(尝试 {attempt + 1}/3): {e}")
                    if attempt == 2:  # 最后一次尝试
                        error_msg = f"无法获取视频信息: {str(e)}"
                        logger.error(f"URLProcessor错误: {error_msg}")
                        if progress_callback:
                            await progress_callback(0, f"错误: {error_msg}")
                        return {"success": False, "error": error_msg}
                    
                    # 等待后重试
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            
            if not video_info:
                error_msg = "无法获取视频信息"
                logger.error(f"URLProcessor错误: {error_msg}")
                if progress_callback:
                    await progress_callback(0, f"错误: {error_msg}")
                return {"success": False, "error": error_msg}
                
            video_title = video_info.get("title", "unknown_video")
            safe_title = self._sanitize_filename(video_title)
            
            if progress_callback:
                await progress_callback(15, f"正在下载音频: {video_title}")
            
            # 设置下载选项 - 下载到files文件夹（按照正确的处理逻辑）
            download_options = DownloadOptions(
                audio_only=True, 
                output_path=settings.FILES_PATH,  # 修正：下载到files文件夹而不是temp
                output_filename=f"{safe_title}_audio.%(ext)s"
            )
            
            # 下载音频文件 - 增强错误处理
            logger.info(f"开始下载音频文件，下载选项: {download_options}")
            
            download_result = None
            for attempt in range(3):  # 重试3次
                try:
                    if progress_callback:
                        await progress_callback(20 + attempt * 5, f"正在下载音频(尝试 {attempt + 1}/3)...")
                    
                    download_result = await downloader.download(url, download_options)
                    if download_result and download_result.get("success"):
                        break
                        
                except Exception as e:
                    logger.warning(f"音频下载失败(尝试 {attempt + 1}/3): {e}")
                    if attempt == 2:  # 最后一次尝试
                        error_msg = f"音频下载失败: {str(e)}"
                        logger.error(f"URLProcessor错误: {error_msg}")
                        if progress_callback:
                            await progress_callback(0, f"错误: {error_msg}")
                        return {"success": False, "error": error_msg}
                    
                    # 等待后重试
                    await asyncio.sleep(3 ** attempt)  # 指数退避
            
            logger.info(f"下载结果: {download_result}")
            
            if not download_result or not download_result.get("success"):
                error_msg = f"音频下载失败: {download_result.get('error', '未知错误') if download_result else '下载器无响应'}"
                logger.error(f"URLProcessor错误: {error_msg}")
                if progress_callback:
                    await progress_callback(0, f"错误: {error_msg}")
                return {"success": False, "error": error_msg}
            
            downloaded_file = download_result["file_path"]
            logger.info(f"下载器返回的文件路径: {downloaded_file}")
            
            if progress_callback:
                await progress_callback(35, "正在查找音频文件...")
            
            # 智能查找实际的音频文件
            logger.info(f"开始查找音频文件，下载文件: {downloaded_file}, 标题: {safe_title}")
            
            # 列出files目录中的所有文件用于调试
            files_list = []
            try:
                import glob
                files_pattern = os.path.join(settings.FILES_PATH, "*")
                files_list = glob.glob(files_pattern)
                logger.info(f"files目录中的文件: {files_list}")
            except Exception as e:
                logger.warning(f"无法列出files目录文件: {e}")
            
            actual_audio_file = await self._find_actual_audio_file(downloaded_file, safe_title)
            logger.info(f"查找到的音频文件: {actual_audio_file}")
            
            if not actual_audio_file or not os.path.exists(actual_audio_file):
                # 提供更详细的错误信息
                error_details = f"无法找到下载的音频文件。下载文件: {downloaded_file}, 查找结果: {actual_audio_file}"
                if files_list:
                    error_details += f", files目录文件: {files_list}"
                
                logger.error(f"URLProcessor错误: {error_details}")
                if progress_callback:
                    await progress_callback(0, f"错误: {error_details}")
                return {"success": False, "error": error_details}
            
            logger.info(f"找到实际音频文件: {actual_audio_file}")
            
            if progress_callback:
                await progress_callback(40, "音频下载完成，开始生成字幕...")
            
            # 创建字幕生成的进度回调
            async def subtitle_progress(progress, message=""):
                # 将进度映射到 40-90 的范围
                total_progress = 40 + (progress * 0.5)
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
            
            if not result.get("success"):
                error_msg = f"字幕生成失败: {result.get('error', '未知错误')}"
                logger.error(f"URLProcessor错误: {error_msg}")
                if progress_callback:
                    await progress_callback(0, f"错误: {error_msg}")
                return {"success": False, "error": error_msg}
            
            # 如果需要翻译
            if translate_to:
                if progress_callback:
                    await progress_callback(90, "正在翻译字幕...")
                
                try:
                    translate_result = await self.subtitle_translator.translate_subtitles(
                        result["subtitle_file"],
                        target_language=translate_to
                    )
                    
                    if translate_result.get("success"):
                        result["subtitle_file"] = translate_result["translated_file"]
                        result["translated"] = True
                    else:
                        logger.warning(f"翻译失败: {translate_result.get('error', '未知错误')}")
                        # 翻译失败不影响主流程，继续使用原字幕
                        
                except Exception as e:
                    logger.warning(f"翻译过程出错: {e}")
                    # 翻译出错不影响主流程
            
            if progress_callback:
                await progress_callback(95, "清理临时文件...")
            
            # 清理临时文件
            try:
                await self._cleanup_temp_files(actual_audio_file, downloaded_file, keep_video=download_video)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
                # 清理失败不影响主流程
            
            if progress_callback:
                await progress_callback(100, "处理完成")
            
            result["video_file"] = actual_audio_file if download_video else None
            result["source_url"] = url
            result["source_type"] = "url"
            
            logger.info(f"URLProcessor成功完成: {video_title}")
            return result
            
        except Exception as e:
            error_msg = f"从URL生成字幕失败: {str(e)}"
            logger.error(f"URLProcessor错误: {error_msg}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            
            if progress_callback:
                await progress_callback(0, f"错误: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def _find_actual_audio_file(self, downloaded_file: str, safe_title: str) -> str:
        """
        智能查找实际的音频文件 - 支持.mhtml格式
        
        Args:
            downloaded_file: 下载器返回的文件路径
            safe_title: 安全的标题名称
            
        Returns:
            str: 实际的音频文件路径
        """
        try:
            import os
            import glob
            import time
            from ..config import settings
            
            logger.info(f"开始查找音频文件 - 下载文件: {downloaded_file}, 标题: {safe_title}")
            
            # 如果下载的就是音频文件，直接返回
            if downloaded_file and os.path.exists(downloaded_file):
                # 检查文件扩展名
                ext = os.path.splitext(downloaded_file)[1].lower()
                logger.info(f"检查下载文件扩展名: {ext}")
                
                # 传统音频格式
                if ext in ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.webm', '.mp4']:
                    logger.info(f"下载文件就是音频文件: {downloaded_file}")
                    return downloaded_file
                    
                # .mhtml格式处理 - YouTube新限制的临时解决方案
                elif ext == '.mhtml':
                    logger.info(f"检测到.mhtml文件，尝试转换为音频: {downloaded_file}")
                    converted_file = await self._convert_mhtml_to_audio(downloaded_file, safe_title)
                    if converted_file:
                        return converted_file
            
            # 如果返回的是.info.json文件，查找对应的音频文件
            if downloaded_file and downloaded_file.endswith('.info.json'):
                base_name = downloaded_file.replace('.info.json', '')
                logger.info(f"处理info.json文件，基础名称: {base_name}")
                
                # 查找可能的音频文件扩展名（包括.mhtml）
                audio_extensions = ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.webm', '.mp4', '.mhtml']
                for ext in audio_extensions:
                    possible_file = base_name + ext
                    logger.debug(f"检查可能的文件: {possible_file}")
                    if os.path.exists(possible_file):
                        logger.info(f"找到对应的文件: {possible_file}")
                        
                        # 如果是.mhtml，尝试转换
                        if ext == '.mhtml':
                            converted_file = await self._convert_mhtml_to_audio(possible_file, safe_title)
                            if converted_file:
                                return converted_file
                        else:
                            return possible_file
            
            # 按文件名模式查找 - 在files目录查找（修正逻辑）
            files_dir = settings.FILES_PATH
            audio_extensions = ['.mp3', '.m4a', '.wav', '.aac', '.ogg', '.webm', '.mp4', '.mhtml']
            logger.info(f"在files目录查找: {files_dir}")
            
            # 查找包含标题的音频文件
            for ext in audio_extensions:
                # 精确匹配
                pattern1 = os.path.join(files_dir, f"{safe_title}_audio{ext}")
                logger.debug(f"检查精确匹配: {pattern1}")
                if os.path.exists(pattern1):
                    logger.info(f"找到精确匹配的文件: {pattern1}")
                    
                    # 如果是.mhtml，尝试转换
                    if ext == '.mhtml':
                        converted_file = await self._convert_mhtml_to_audio(pattern1, safe_title)
                        if converted_file:
                            return converted_file
                    else:
                        return pattern1
                
                # 模糊匹配
                pattern2 = os.path.join(files_dir, f"*{safe_title}*{ext}")
                matches = glob.glob(pattern2)
                logger.debug(f"模糊匹配 {pattern2}: {matches}")
                if matches:
                    # 返回最新的文件
                    newest = max(matches, key=os.path.getctime)
                    logger.info(f"找到模糊匹配的最新文件: {newest}")
                    
                    # 如果是.mhtml，尝试转换
                    if ext == '.mhtml':
                        converted_file = await self._convert_mhtml_to_audio(newest, safe_title)
                        if converted_file:
                            return converted_file
                    else:
                        return newest
            
            # 查找最新创建的音频文件（不依赖标题，包括.mhtml）
            audio_files = []
            for ext in audio_extensions:
                pattern = os.path.join(files_dir, f"*{ext}")
                found_files = glob.glob(pattern)
                audio_files.extend(found_files)
                logger.debug(f"扩展名 {ext} 的文件: {found_files}")
            
            logger.info(f"找到的所有音频文件: {audio_files}")
            
            if audio_files:
                # 返回最新创建的音频文件
                newest_file = max(audio_files, key=os.path.getctime)
                file_age = time.time() - os.path.getctime(newest_file)
                logger.info(f"最新音频文件: {newest_file}, 创建时间间隔: {file_age}秒")
                
                # 确保文件是最近10分钟内创建的（增加时间窗口）
                if file_age < 600:  # 10分钟
                    logger.info(f"返回最新的音频文件: {newest_file}")
                    
                    # 如果是.mhtml，尝试转换
                    if newest_file.endswith('.mhtml'):
                        converted_file = await self._convert_mhtml_to_audio(newest_file, safe_title)
                        if converted_file:
                            return converted_file
                    else:
                        return newest_file
                else:
                    logger.warning(f"最新文件太旧 ({file_age}秒)，跳过")
            
            logger.warning("未找到任何音频文件")
            return None
            
        except Exception as e:
            logger.error(f"查找音频文件失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None

    
    async def _convert_mhtml_to_audio(self, mhtml_file: str, safe_title: str) -> Optional[str]:
        """
        尝试将.mhtml文件转换为音频文件
        
        Args:
            mhtml_file: .mhtml文件路径
            safe_title: 安全的标题名称
            
        Returns:
            str: 转换后的音频文件路径，失败时返回None
        """
        try:
            import subprocess
            import json
            from ..config import settings
            
            logger.info(f"尝试转换.mhtml文件: {mhtml_file}")
            
            # 检查文件是否存在
            if not os.path.exists(mhtml_file):
                logger.warning(f".mhtml文件不存在: {mhtml_file}")
                return None
            
            # 检查文件大小，如果太小可能不包含音频数据
            file_size = os.path.getsize(mhtml_file)
            logger.info(f".mhtml文件大小: {file_size} 字节")
            
            if file_size < 1024:  # 小于1KB，很可能只是错误页面
                logger.warning(f".mhtml文件太小，可能不包含音频数据: {file_size} 字节")
                return None
            
            # 尝试方法1: 使用ffmpeg直接处理（如果.mhtml包含音频数据）
            output_audio = os.path.join(settings.TEMP_PATH, f"{safe_title}_converted.mp3")
            try:
                cmd = [
                    'ffmpeg', '-y',  # -y 覆盖输出文件
                    '-i', mhtml_file,
                    '-vn',  # 不处理视频
                    '-acodec', 'mp3',
                    '-ab', '128k',
                    output_audio
                ]
                
                logger.info(f"尝试使用ffmpeg转换: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0 and os.path.exists(output_audio):
                    output_size = os.path.getsize(output_audio)
                    if output_size > 1024:  # 转换成功且文件有内容
                        logger.info(f"ffmpeg转换成功: {output_audio}, 大小: {output_size} 字节")
                        return output_audio
                else:
                    logger.warning(f"ffmpeg转换失败: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.warning("ffmpeg转换超时")
            except FileNotFoundError:
                logger.warning("ffmpeg不可用，跳过直接转换")
            except Exception as e:
                logger.warning(f"ffmpeg转换异常: {e}")
            
            # 尝试方法2: 重新下载（使用不同的参数）
            try:
                # 检查是否有对应的.info.json文件
                info_file = mhtml_file.replace('.mhtml', '.info.json')
                if os.path.exists(info_file):
                    logger.info(f"找到info.json文件，尝试重新下载: {info_file}")
                    
                    # 读取视频信息
                    with open(info_file, 'r', encoding='utf-8') as f:
                        video_info = json.load(f)
                    
                    # 获取原始URL
                    original_url = video_info.get('original_url') or video_info.get('webpage_url')
                    if original_url:
                        logger.info(f"尝试重新下载音频: {original_url}")
                        
                        # 使用更强制的音频下载选项
                        from ..downloaders.downloader_factory import downloader_factory
                        from ..downloaders import DownloadOptions
                        
                        downloader = downloader_factory.get_downloader(original_url)
                        if downloader:
                            # 强制音频格式下载
                            download_options = DownloadOptions(
                                audio_only=True,
                                format='bestaudio',  # 强制最佳音频
                                output_path=settings.TEMP_PATH,
                                output_filename=f"{safe_title}_retry.%(ext)s"
                            )
                            
                            retry_result = await downloader.download(original_url, download_options)
                            if retry_result and retry_result.get("success"):
                                retry_file = retry_result["file_path"]
                                if retry_file and os.path.exists(retry_file) and not retry_file.endswith('.mhtml'):
                                    logger.info(f"重新下载成功: {retry_file}")
                                    return retry_file
                
            except Exception as e:
                logger.warning(f"重新下载失败: {e}")
            
            # 如果所有方法都失败，返回None
            logger.warning(f"无法转换.mhtml文件为音频: {mhtml_file}")
            return None
            
        except Exception as e:
            logger.error(f"转换.mhtml文件失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
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
"""
AVD Web版本 - 字幕处理器（重构版）

使用模块化架构，协调各个子模块完成字幕处理任务
采用faster-whisper最高品质和SentencePiece翻译，自动清理临时文件
"""

import os
import asyncio
from typing import Dict, List, Optional, Callable, Any
import logging

from .config import settings
from ..utils.logger import get_logger

# 导入拆分的模块
from .subtitle_modules import (
    AudioProcessor,
    WhisperModelManager,
    SubtitleTranslator,
    SubtitleFileHandler,
    SubtitleGenerator,
    URLProcessor,
    SubtitleEffects
)

logger = get_logger(__name__)


class SubtitleProcessor:
    """
    字幕处理器主类
    
    协调各个子模块完成字幕处理任务，包括：
    - 音频提取和处理（使用faster-whisper最高品质）
    - SentencePiece翻译（最高品质）
    - 自动清理临时文件
    - 浏览器下载回传
    """
    
    def __init__(self):
        """初始化字幕处理器和所有子模块"""
        # 初始化各个子模块
        self.audio_processor = AudioProcessor()
        self.model_manager = WhisperModelManager()
        from .subtitle_modules.subtitle_translator_optimized import SubtitleTranslatorOptimized
        self.translator = SubtitleTranslatorOptimized()
        self.file_handler = SubtitleFileHandler()
        self.subtitle_generator = SubtitleGenerator()
        self.url_processor = URLProcessor()
        self.effects_processor = SubtitleEffects()
        
        # 临时文件跟踪列表
        self.temp_files = []
        
        logger.info("字幕处理器初始化完成（使用faster-whisper最高品质+优化版翻译器）")
    
    def _add_temp_file(self, file_path: str):
        """添加临时文件到跟踪列表"""
        if file_path and file_path not in self.temp_files:
            self.temp_files.append(file_path)
    
    async def _cleanup_temp_files(self):
        """自动清理临时文件"""
        try:
            cleanup_count = 0
            for temp_file in self.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        logger.info(f"已清理临时文件: {temp_file}")
                        cleanup_count += 1
                except Exception as e:
                    logger.warning(f"清理临时文件失败 {temp_file}: {e}")
            
            self.temp_files.clear()
            logger.info(f"自动清理完成，共清理 {cleanup_count} 个临时文件")
            
        except Exception as e:
            logger.error(f"自动清理临时文件失败: {e}")
    
    # =============================================================
    # 公共API接口（保持兼容性）
    # =============================================================
    
    def get_supported_languages(self) -> Dict[str, Any]:
        """获取支持的语言列表"""
        return self.translator.get_supported_languages()
    
    def get_translation_config(self) -> Dict[str, Any]:
        """获取翻译配置信息"""
        return self.translator.get_translation_config()
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return self.model_manager.get_model_info()
    
    def reload_config(self) -> Dict[str, Any]:
        """重新加载配置"""
        try:
            # 清除各模块的缓存
            self.model_manager.clear_cache()
            
            # 重新初始化翻译器（优化版）
            from .subtitle_modules.subtitle_translator_optimized import SubtitleTranslatorOptimized
            self.translator = SubtitleTranslatorOptimized()
            
            logger.info("配置重新加载完成")
            return {
                "success": True,
                "message": "配置重新加载成功",
                "cache_cleared": True
            }
            
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # =============================================================
    # 字幕生成相关接口（新流程）
    # =============================================================
    
    async def generate_subtitles(self,
                               video_path: str,
                               language: str = "auto",
                               model_size: str = None,
                               progress_callback: Optional[Callable] = None,
                               video_title: str = None,
                               auto_translate: bool = True,
                               target_language: str = "zh") -> Dict[str, Any]:
        """
        从视频文件生成字幕（新流程）
        1. 音频提取（使用faster-whisper最高品质）
        2. SentencePiece翻译（最高品质）
        3. 自动清理临时文件
        
        Args:
            video_path: 视频文件路径
            language: 语言代码
            model_size: 模型大小（默认使用最高品质）
            progress_callback: 进度回调函数
            video_title: 视频标题
            auto_translate: 是否自动翻译
            target_language: 翻译目标语言
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 使用最高品质模型
            if not model_size:
                model_size = "large-v3"  # 强制使用最高品质模型
            
            # 辅助函数：智能调用progress_callback
            async def safe_progress_callback(progress, message=""):
                if progress_callback:
                    import inspect
                    if inspect.iscoroutinefunction(progress_callback):
                        await progress_callback(progress, message)
                    else:
                        progress_callback(progress, message)
            
            await safe_progress_callback(5, "开始处理视频文件...")
            
            # 1. 生成原始字幕（使用faster-whisper最高品质）
            subtitle_result = await self.subtitle_generator.generate_from_video(
                video_path=video_path,
                language=language,
                model_size=model_size,
                progress_callback=None,  # 避免异步回调警告
                video_title=video_title
            )
            
            if not subtitle_result.get("success"):
                return subtitle_result
            
            original_subtitle_file = subtitle_result["subtitle_file"]
            
            # 2. SentencePiece翻译（如果需要）
            if auto_translate and target_language != language:
                await safe_progress_callback(70, "开始SentencePiece翻译...")
                
                translate_result = await self.translator.translate_subtitles(
                    subtitle_path=original_subtitle_file,
                    source_language=language,
                    target_language=target_language,
                    progress_callback=None  # 避免异步回调警告
                )
                
                if translate_result.get("success"):
                    # 删除原始字幕文件，保留翻译版本
                    self._add_temp_file(original_subtitle_file)
                    subtitle_result["subtitle_file"] = translate_result["translated_file"]
                    subtitle_result["translated"] = True
                    subtitle_result["translation_info"] = translate_result
                
            await safe_progress_callback(98, "准备下载文件...")
            
            # 3. 自动清理临时文件（保留最终结果文件）
            await self._cleanup_temp_files()
            
            await safe_progress_callback(100, "处理完成，准备下载")
            
            # 添加下载相关信息
            subtitle_result.update({
                "ready_for_download": True,
                "model_quality": "最高品质(large-v3)",
                "translation_quality": "SentencePiece最高品质" if auto_translate else None,
                "temp_files_cleaned": True
            })
            
            return subtitle_result
            
        except Exception as e:
            logger.error(f"生成字幕失败: {e}")
            # 清理临时文件
            await self._cleanup_temp_files()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_subtitles_from_url(self,
                                        url: str,
                                        language: str = "auto",
                                        model_size: str = None,
                                        translate_to: Optional[str] = "zh",
                                        download_video: bool = False,
                                        progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        从URL生成字幕（新流程）
        1. 下载到服务器files文件夹临时存储
        2. 音频提取（使用faster-whisper最高品质）
        3. SentencePiece翻译（最高品质）
        4. 自动清理临时文件
        
        Args:
            url: 视频URL
            language: 语言代码
            model_size: 模型大小（默认使用最高品质）
            translate_to: 翻译目标语言
            download_video: 是否保留视频文件
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 使用最高品质模型
            if not model_size:
                model_size = "large-v3"  # 强制使用最高品质模型
            
            # 辅助函数：智能调用progress_callback
            async def safe_progress_callback(progress, message=""):
                if progress_callback:
                    import inspect
                    if inspect.iscoroutinefunction(progress_callback):
                        await progress_callback(progress, message)
                    else:
                        progress_callback(progress, message)
            
            await safe_progress_callback(5, "开始从URL下载...")
            
            # 1. 下载视频/音频到files文件夹并生成字幕
            result = await self.url_processor.generate_subtitles_from_url(
                url=url,
                language=language,
                model_size=model_size,
                translate_to=None,  # 暂时不翻译，后面用SentencePiece
                download_video=download_video,
                progress_callback=None  # 避免异步回调警告
            )
            
            if not result.get("success"):
                return result
            
            # 记录下载的文件用于清理
            if result.get("video_file") and not download_video:
                self._add_temp_file(result["video_file"])
            
            # 2. SentencePiece翻译（如果需要）
            if translate_to and translate_to != language:
                await safe_progress_callback(75, "开始SentencePiece翻译...")
                
                translate_result = await self.translator.translate_subtitles(
                    subtitle_path=result["subtitle_file"],
                    source_language=language,
                    target_language=translate_to,
                    progress_callback=None  # 避免异步回调警告
                )
                
                if translate_result.get("success"):
                    # 删除原始字幕文件，保留翻译版本
                    self._add_temp_file(result["subtitle_file"])
                    result["subtitle_file"] = translate_result["translated_file"]
                    result["translated"] = True
                    result["translation_info"] = translate_result
            
            await safe_progress_callback(98, "准备下载文件...")
            
            # 3. 自动清理临时文件
            await self._cleanup_temp_files()
            
            await safe_progress_callback(100, "处理完成，准备下载")
            
            # 添加下载相关信息
            result.update({
                "ready_for_download": True,
                "model_quality": "最高品质(large-v3)",
                "translation_quality": "SentencePiece最高品质" if translate_to else None,
                "temp_files_cleaned": True
            })
            
            return result
            
        except Exception as e:
            logger.error(f"从URL生成字幕失败: {e}")
            # 清理临时文件
            await self._cleanup_temp_files()
            return {
                "success": False,
                "error": str(e)
            }
    
    # =============================================================
    # 字幕翻译相关接口（新流程）
    # =============================================================
    
    async def translate_subtitles(self,
                                subtitle_path: str,
                                source_language: str = "auto",
                                target_language: str = "zh",
                                translation_method: str = None,
                                progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        翻译字幕文件（新流程）
        1. 字幕文件上传到服务器files文件夹临时存储
        2. SentencePiece翻译（最高品质）
        3. 自动清理临时文件
        
        Args:
            subtitle_path: 字幕文件路径
            source_language: 源语言
            target_language: 目标语言
            translation_method: 翻译方法（兼容参数，强制使用SentencePiece）
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 翻译结果
        """
        try:
            # 辅助函数：智能调用progress_callback
            async def safe_progress_callback(progress, message=""):
                if progress_callback:
                    import inspect
                    if inspect.iscoroutinefunction(progress_callback):
                        await progress_callback(progress, message)
                    else:
                        progress_callback(progress, message)
            
            await safe_progress_callback(5, "开始SentencePiece翻译...")
            
            # 强制使用SentencePiece翻译（最高品质）
            # 注意：暂时不传递progress_callback避免异步警告
            result = await self.translator.translate_subtitles(
                subtitle_path=subtitle_path,
                source_language=source_language,
                target_language=target_language,
                progress_callback=None  # 避免异步回调警告
            )
            
            if not result.get("success"):
                return result
            
            await safe_progress_callback(98, "准备下载文件...")
            
            # 自动清理临时文件（保留翻译结果）
            if subtitle_path != result.get("translated_file"):
                self._add_temp_file(subtitle_path)
            
            await self._cleanup_temp_files()
            
            await safe_progress_callback(100, "翻译完成，准备下载")
            
            # 添加下载相关信息和字段映射
            result.update({
                "ready_for_download": True,
                "translation_quality": "SentencePiece最高品质",
                "temp_files_cleaned": True,
                "subtitle_file": result.get("translated_file")  # 映射字段用于SSE处理
            })
            
            return result
            
        except Exception as e:
            logger.error(f"翻译字幕失败: {e}")
            # 清理临时文件
            await self._cleanup_temp_files()
            return {
                "success": False,
                "error": str(e)
            }
    
    # =============================================================
    # 字幕特效和烧录相关接口
    # =============================================================
    
    async def burn_subtitles_to_video(self,
                                    video_path: str,
                                    subtitle_path: str,
                                    output_path: str = None,
                                    subtitle_style: Dict[str, Any] = None,
                                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        将字幕烧录到视频中
        
        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            output_path: 输出文件路径
            subtitle_style: 字幕样式
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 烧录结果
        """
        return await self.effects_processor.burn_subtitles_to_video(
            video_path=video_path,
            subtitle_path=subtitle_path,
            output_path=output_path,
            subtitle_style=subtitle_style,
            progress_callback=progress_callback
        )
    
    def get_default_subtitle_style(self) -> Dict[str, Any]:
        """获取默认字幕样式"""
        return self.effects_processor.get_default_subtitle_style()
    
    # =============================================================
    # 辅助功能接口
    # =============================================================
    
    def get_supported_subtitle_formats(self) -> List[str]:
        """获取支持的字幕格式"""
        return self.file_handler.get_supported_formats()
    
    def get_quality_options(self) -> Dict[str, str]:
        """获取质量选项"""
        return {
            "large-v3": "最高品质（faster-whisper + SentencePiece）",
            "large": "高品质",
            "medium": "中等品质",
            "base": "基础品质",
            "small": "较低品质",
            "tiny": "最低品质"
        }
    
    # =============================================================
    # 私有辅助方法（保持兼容性）
    # =============================================================
    
    def _parse_srt_file(self, srt_path: str) -> List[Dict]:
        """解析SRT字幕文件（兼容性方法）"""
        return self.file_handler.parse_srt_file(srt_path)
    
    def _save_srt_file(self, subtitles: List[Dict], output_path: str):
        """保存SRT字幕文件（兼容性方法）"""
        return self.file_handler.save_srt_file(subtitles, output_path)
    
    def _sanitize_filename(self, filename: str, max_length: int = 200, default_name: str = "subtitle") -> str:
        """清理文件名（兼容性方法）"""
        return self.file_handler.sanitize_filename(filename, max_length, default_name)
    
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳（兼容性方法）"""
        return self.file_handler.format_timestamp(seconds)
    
    # =============================================================
    # 模型管理相关方法（委托给模型管理器）
    # =============================================================
    
    def _load_whisper_model(self, model_size: str = None):
        """加载Whisper模型（兼容性方法）"""
        return self.model_manager.load_model(model_size)
    
    def _get_model_specific_options(self, model_size: str, language: str) -> dict:
        """获取模型特定选项（兼容性方法）"""
        return self.model_manager.get_model_specific_options(model_size, language)
    
    def _get_retry_options(self, model_size: str, language: str) -> dict:
        """获取重试选项（兼容性方法）"""
        return self.model_manager.get_retry_options(model_size, language)
    
    # =============================================================
    # 音频处理相关方法（委托给音频处理器）
    # =============================================================
    
    async def _extract_audio(self, video_path: str) -> str:
        """从视频中提取音频（兼容性方法）"""
        return await self.audio_processor.extract_audio(video_path)
    
    # =============================================================
    # 翻译相关方法（委托给翻译器）
    # =============================================================
    
    def detect_language(self, text: str) -> str:
        """检测文本语言（兼容性方法）"""
        return self.translator.detect_language(text)
    
    async def translate_text(self, text: str, target_lang: str = "zh", source_lang: str = "auto") -> str:
        """翻译文本（兼容性方法）"""
        return await self.translator.translate_text(text, target_lang, source_lang)
    
    async def batch_translate(self, texts: List[str], target_language: str = "zh") -> List[str]:
        """批量翻译（兼容性方法）"""
        return await self.translator.batch_translate(texts, target_language)


# =============================================================
# 兼容性函数（保持向后兼容）
# =============================================================

# 全局实例
_subtitle_processor_instance = None


def get_subtitle_processor_instance():
    """获取字幕处理器实例（单例模式）"""
    global _subtitle_processor_instance
    if _subtitle_processor_instance is None:
        _subtitle_processor_instance = SubtitleProcessor()
    return _subtitle_processor_instance


def get_subtitle_processor():
    """获取字幕处理器（别名函数）"""
    return get_subtitle_processor_instance()


# =============================================================
# 向后兼容的类别名
# =============================================================

class ImprovedTranslator:
    """
    兼容性类：向后兼容原有的ImprovedTranslator
    实际委托给SubtitleTranslator处理
    """
    
    def __init__(self):
        self._translator = SubtitleTranslator()
        logger.warning("ImprovedTranslator is deprecated, use SubtitleTranslator instead")
    
    def __getattr__(self, name):
        """委托所有方法调用给SubtitleTranslator"""
        return getattr(self._translator, name)
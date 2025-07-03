"""
AVD Web版本 - 字幕处理器（重构版）

使用模块化架构，协调各个子模块完成字幕处理任务
采用faster-whisper最高品质和SentencePiece翻译，自动清理临时文件
"""

import os
import asyncio
from typing import Dict, List, Optional, Callable, Any
import logging
from pathlib import Path

from .config import settings
from ..utils.logger import get_logger

# 添加任务管理器引用
try:
    from ..api.routers.subtitles.subtitle_processor import task_manager
except ImportError:
    # 如果没有task_manager，创建一个简单的替代
    class SimpleTaskManager:
        def is_cancelled(self, task_id):
            return False
    task_manager = SimpleTaskManager()

# 导入拆分的模块
from .subtitle_modules import (
    AudioProcessor,
    WhisperModelManager,
    SubtitleTranslator,
    SubtitleGenerator,
    URLProcessor,
    SubtitleEffects
)

# 使用增强版字幕文件处理器
from .subtitle_modules.subtitle_file_handler_enhanced import EnhancedSubtitleFileHandler

logger = get_logger(__name__)


class SubtitleProcessor:
    """
    重写优化的字幕处理器
    
    核心功能：
    1. 从URL生成字幕
    2. 从文件生成字幕  
    3. 翻译字幕
    4. 进度跟踪和错误处理
    
    特点：
    - 统一的错误处理
    - 自动资源清理
    - 实时进度反馈
    - 智能参数优化
    """
    
    def __init__(self):
        """初始化字幕处理器"""
        # 核心模块
        self.audio_processor = AudioProcessor()
        self.model_manager = WhisperModelManager()
        self.file_handler = EnhancedSubtitleFileHandler()
        self.url_processor = URLProcessor()
        
        # 使用标准翻译器
        from .subtitle_modules.subtitle_translator import SubtitleTranslator
        self.translator = SubtitleTranslator()
        logger.info("使用高性能标准翻译器")
        
        # 临时文件管理
        self.temp_files = []
        
        logger.info("字幕处理器初始化完成")
    
    def _add_temp_file(self, file_path: str):
        """添加临时文件到清理列表"""
        if file_path and file_path not in self.temp_files:
            self.temp_files.append(file_path)
    
    async def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            cleaned_count = 0
            for temp_file in self.temp_files[:]:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        cleaned_count += 1
                        logger.debug(f"清理临时文件: {temp_file}")
                except Exception as e:
                    logger.warning(f"清理文件失败 {temp_file}: {e}")
            
            self.temp_files.clear()
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 个临时文件")
                
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")

    async def process_from_url(self, 
                              video_url: str,
                              source_language: str = 'auto',
                              model_size: str = 'large-v3',
                              target_language: Optional[str] = None,
                              quality_mode: str = 'balance',
                              task_id: Optional[str] = None,
                              progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        从URL生成字幕 - 重写优化版本
        
        Args:
            video_url: 视频URL
            source_language: 源语言 (auto/zh/en/ja等)
            model_size: 模型大小 (large-v3/large/medium等)
            target_language: 目标翻译语言 (可选)
            quality_mode: 质量模式 (quality/balance/speed)
            task_id: 任务ID (用于取消检查)
            progress_callback: 进度回调函数
        
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"开始从URL生成字幕: {video_url}")
            
            if progress_callback:
                await progress_callback(15, "验证URL...")
            
            # 1. 验证URL
            if not self._validate_url(video_url):
                return {'success': False, 'error': '无效的视频URL'}
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            if progress_callback:
                await progress_callback(20, "开始下载和处理...")
            
            # 2. 使用URL处理器处理，传递进度回调
            result = await self.url_processor.generate_subtitles_from_url(
                url=video_url,
                language=source_language,
                model_size=model_size,
                download_video=False,
                progress_callback=progress_callback  # 传递进度回调
            )
            
            if not result.get('success'):
                return {
                    'success': False,
                    'error': f"URL处理失败: {result.get('error', '未知错误')}"
                }
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            # 3. 翻译处理 (如果需要)
            if target_language and target_language != source_language:
                if progress_callback:
                    await progress_callback(85, "正在翻译字幕...")
                
                subtitle_file = result.get('subtitle_file')
                if subtitle_file:
                    translate_result = await self._translate_subtitle_internal(
                        subtitle_file, source_language, target_language, task_id
                    )
                    
                    if translate_result.get('success'):
                        result['subtitle_file'] = translate_result['translated_file']
                        result['translated'] = True
                        result['target_language'] = target_language
                        self._add_temp_file(subtitle_file)  # 原文件标记为临时
            
            if progress_callback:
                await progress_callback(95, "清理临时文件...")
            
            # 4. 清理临时文件
            await self._cleanup_temp_files()
            
            if progress_callback:
                await progress_callback(100, "处理完成")
            
            logger.info(f"从URL生成字幕完成: {result.get('title', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"从URL生成字幕失败: {e}")
            await self._cleanup_temp_files()
            return {'success': False, 'error': str(e)}

    async def process_from_file(self, 
                            video_file_path: str,
                            source_language: str = 'auto',
                            model_size: str = 'large-v3',
                            target_language: Optional[str] = None,
                            quality_mode: str = 'balance',
                            task_id: Optional[str] = None,
                            video_title: Optional[str] = None,
                            progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        从文件生成字幕 - 重写优化版本
        
        Args:
            video_file_path: 视频文件路径
            source_language: 源语言 (auto/zh/en/ja等)
            model_size: 模型大小 (large-v3/large/medium等)
            target_language: 目标翻译语言 (可选)
            quality_mode: 质量模式 (quality/balance/speed)
            task_id: 任务ID (用于取消检查)
            video_title: 视频标题 (可选)
            progress_callback: 进度回调函数
        
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"开始从文件生成字幕: {video_file_path}")
            
            if progress_callback:
                await progress_callback(15, "验证文件...")
            
            # 1. 验证文件存在
            if not os.path.exists(video_file_path):
                return {'success': False, 'error': '视频文件不存在'}
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            if progress_callback:
                await progress_callback(20, "提取音频...")
            
            # 2. 提取音频
            audio_path = await self.audio_processor.extract_audio(
                video_file_path
            )
            
            if not audio_path:
                return {'success': False, 'error': '音频提取失败'}
            
            self._add_temp_file(audio_path)
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            if progress_callback:
                await progress_callback(30, "加载语音识别模型...")
            
            # 3. 生成字幕的进度回调包装器
            async def subtitle_progress_wrapper(progress: float, message: str = ""):
                # 将字幕生成的进度映射到30-80的范围
                mapped_progress = 30 + (progress * 0.5)  # 50%的进度范围给字幕生成
                if progress_callback:
                    await progress_callback(mapped_progress, message)
            
            # 4. 生成字幕
            result = await self._generate_subtitles_from_audio_internal(
                audio_path=audio_path,
                source_language=source_language,
                model_size=model_size,
                quality_mode=quality_mode,
                task_id=task_id,
                video_title=video_title,
                progress_callback=subtitle_progress_wrapper
            )
            
            if not result.get('success'):
                return result
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            # 5. 翻译处理 (如果需要)
            if target_language and target_language != source_language:
                if progress_callback:
                    await progress_callback(85, "正在翻译字幕...")
                
                subtitle_file = result.get('subtitle_file')
                if subtitle_file:
                    translate_result = await self._translate_subtitle_internal(
                        subtitle_file, source_language, target_language, task_id
                    )
                    
                    if translate_result.get('success'):
                        result['subtitle_file'] = translate_result['translated_file']
                        result['translated'] = True
                        result['target_language'] = target_language
                        self._add_temp_file(subtitle_file)  # 原文件标记为临时
            
            if progress_callback:
                await progress_callback(95, "清理临时文件...")
            
            # 6. 清理临时文件
            await self._cleanup_temp_files()
            
            if progress_callback:
                await progress_callback(100, "处理完成")
            
            logger.info(f"从文件生成字幕完成: {result.get('title', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"从文件生成字幕失败: {e}")
            await self._cleanup_temp_files()
            return {'success': False, 'error': str(e)}

    async def translate_subtitle_file(self, 
                                   subtitle_path: str,
                                   source_language: str = 'auto',
                                   target_language: str = 'zh',
                                   translation_method: str = 'optimized',
                                   quality_mode: str = 'balance',
                                   task_id: Optional[str] = None,
                                   original_title: Optional[str] = None,
                                   progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        翻译字幕文件 - 重写优化版本
        
        Args:
            subtitle_path: 字幕文件路径
            source_language: 源语言
            target_language: 目标语言
            translation_method: 翻译方法
            quality_mode: 质量模式
            task_id: 任务ID (用于取消检查)
            original_title: 原始标题 (可选)
            progress_callback: 进度回调函数
        
        Returns:
            翻译结果字典
        """
        try:
            logger.info(f"开始翻译字幕: {subtitle_path}")
            
            if progress_callback:
                await progress_callback(15, "验证字幕文件...")
            
            # 1. 验证文件存在
            if not os.path.exists(subtitle_path):
                return {'success': False, 'error': '字幕文件不存在'}
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            if progress_callback:
                await progress_callback(20, "准备翻译...")
            
            # 2. 翻译进度回调包装器
            async def translate_progress_wrapper(progress: float, message: str = ""):
                # 将翻译进度映射到20-95的范围
                mapped_progress = 20 + (progress * 0.75)  # 75%的进度范围给翻译
                if progress_callback:
                    await progress_callback(mapped_progress, message)
            
            # 3. 执行翻译
            result = await self._translate_subtitle_internal(
                subtitle_path=subtitle_path,
                source_language=source_language,
                target_language=target_language,
                task_id=task_id,
                progress_callback=translate_progress_wrapper
            )
            
            if not result.get('success'):
                return result
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            if progress_callback:
                await progress_callback(95, "完成翻译...")
            
            # 4. 处理结果
            result['original_title'] = original_title
            result['source_language'] = source_language
            result['target_language'] = target_language
            result['translation_method'] = translation_method
            
            if progress_callback:
                await progress_callback(100, "翻译完成")
            
            logger.info(f"字幕翻译完成: {result.get('translated_file', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"翻译字幕失败: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_subtitles_from_audio_internal(self, 
                                                   audio_path: str, 
                                                   source_language: str = 'auto', 
                                                   model_size: str = 'large-v3',
                                                   quality_mode: str = 'balance',
                                                   task_id: Optional[str] = None,
                                                   video_title: Optional[str] = None,
                                                   progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        从音频文件生成字幕的内部方法
        
        Args:
            audio_path: 音频文件路径
            source_language: 源语言
            model_size: 模型大小
            quality_mode: 质量模式
            task_id: 任务ID
            video_title: 视频标题
            progress_callback: 进度回调函数
        
        Returns:
            生成结果
        """
        try:
            if progress_callback:
                await progress_callback(5, "加载语音识别模型...")
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            # 加载Whisper模型
            model = self.model_manager.load_model(model_size)
            if not model:
                return {'success': False, 'error': f'无法加载模型: {model_size}'}
            
            if progress_callback:
                await progress_callback(15, "开始语音识别...")
            
            # 转录配置
            transcribe_options = {
                'language': None if source_language == 'auto' else source_language,
                'beam_size': self._get_beam_size(quality_mode),
                'best_of': self._get_best_of(quality_mode),
                'vad_filter': True,
                'vad_parameters': dict(min_silence_duration_ms=500),
                'word_timestamps': True
            }
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            # 执行转录 - 使用线程池异步执行同步的transcribe方法
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            def transcribe_sync():
                """同步执行转录"""
                return model.transcribe(audio_path, **transcribe_options)
            
            # 在线程池中异步执行转录
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                # 提交转录任务
                future = loop.run_in_executor(executor, transcribe_sync)
                
                # 在等待转录完成的同时更新进度
                progress_step = 0
                while not future.done():
                    await asyncio.sleep(1)  # 等待1秒
                    progress_step += 5
                    current_progress = min(85, 15 + progress_step)  # 15-85范围内的进度
                    
                    if progress_callback:
                        await progress_callback(current_progress, "正在进行语音识别...")
                    
                    # 检查任务是否被取消
                    if task_id and self._is_task_cancelled(task_id):
                        return {'success': False, 'error': '任务已被取消'}
                
                # 获取转录结果
                segments, info = await future
            
            if progress_callback:
                await progress_callback(90, "生成字幕文件...")
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            # 生成字幕文件
            subtitle_file = await self.file_handler.save_subtitles_from_segments(
                segments=list(segments),
                video_title=video_title,
                format_type="srt"
            )
            
            if progress_callback:
                await progress_callback(100, "字幕生成完成")
            
            return {
                'success': True,
                'subtitle_file': subtitle_file,
                'language': info.language if hasattr(info, 'language') else source_language,
                'duration': info.duration if hasattr(info, 'duration') else 0,
                'title': video_title or 'Unknown'
            }
            
        except Exception as e:
            logger.error(f"从音频生成字幕失败: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _translate_subtitle_internal(self, 
                                        subtitle_path: str, 
                                        source_language: str, 
                                        target_language: str, 
                                        task_id: Optional[str] = None,
                                        progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        内部字幕翻译方法
        
        Args:
            subtitle_path: 字幕文件路径
            source_language: 源语言
            target_language: 目标语言
            task_id: 任务ID
            progress_callback: 进度回调函数
        
        Returns:
            翻译结果
        """
        try:
            if progress_callback:
                await progress_callback(5, "加载字幕文件...")
            
            # 检查任务是否被取消
            if task_id and self._is_task_cancelled(task_id):
                return {'success': False, 'error': '任务已被取消'}
            
            if progress_callback:
                await progress_callback(10, "初始化翻译器...")
            
            # 使用优化翻译器
            translator = ImprovedTranslator()
            
            if progress_callback:
                await progress_callback(20, "开始翻译...")
            
            # 创建翻译进度回调
            async def translation_progress(progress: float, message: str = ""):
                # 将翻译进度映射到20-90的范围
                mapped_progress = 20 + (progress * 0.7)
                if progress_callback:
                    await progress_callback(mapped_progress, message)
            
            # 执行翻译
            result = await translator.translate_subtitles(
                subtitle_path=subtitle_path,
                target_language=target_language,
                source_language=source_language,
                progress_callback=translation_progress,
                original_title=None
            )
            
            if progress_callback:
                await progress_callback(95, "翻译完成...")
            
            if result.get('success'):
                if progress_callback:
                    await progress_callback(100, "处理完成")
                
                return {
                    'success': True,
                    'translated_file': result['translated_file'],
                    'source_language': source_language,
                    'target_language': target_language,
                    'translation_stats': result.get('stats', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', '翻译失败')
                }
                
        except Exception as e:
            logger.error(f"内部翻译处理失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _is_task_cancelled(self, task_id: str) -> bool:
        """检查任务是否被取消"""
        try:
            return task_manager.is_cancelled(task_id)
        except Exception:
            return False
    
    def _get_beam_size(self, quality_mode: str) -> int:
        """根据质量模式获取beam size"""
        quality_map = {'speed': 1, 'balance': 3, 'quality': 5}
        return quality_map.get(quality_mode, 3)
    
    def _get_best_of(self, quality_mode: str) -> int:
        """根据质量模式获取best of参数"""
        quality_map = {'speed': 1, 'balance': 3, 'quality': 5}
        return quality_map.get(quality_mode, 3)
    
    # 兼容性方法
    async def generate_subtitles(self, *args, **kwargs):
        """兼容旧API的方法"""
        return await self.process_from_file(*args, **kwargs)
    
    async def generate_subtitles_from_url(self, *args, **kwargs):
        """兼容旧API的方法"""
        return await self.process_from_url(*args, **kwargs)
    
    async def translate_subtitles(self, *args, **kwargs):
        """兼容旧API的方法"""
        return await self.translate_subtitle_file(*args, **kwargs)

    # 工具方法
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return {
            'auto': '自动检测',
            'zh': '中文', 'en': '英语', 'ja': '日语', 'ko': '韩语',
            'fr': '法语', 'de': '德语', 'es': '西班牙语', 'it': '意大利语',
            'pt': '葡萄牙语', 'ru': '俄语', 'ar': '阿拉伯语', 'hi': '印地语'
        }
    
    def get_supported_models(self) -> Dict[str, str]:
        """获取支持的模型列表"""
        return {
            'large-v3': '最高质量 (推荐)',
            'large': '高质量',
            'medium': '中等质量',
            'base': '基础质量', 
            'small': '较低质量',
            'tiny': '最低质量'
        }
    
    def get_quality_modes(self) -> Dict[str, str]:
        """获取质量模式列表"""
        return {
            'quality': '最高质量 (速度较慢)',
            'balance': '平衡模式 (推荐)',
            'speed': '快速模式 (质量较低)'
        }


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
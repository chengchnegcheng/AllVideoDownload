"""
字幕生成器模块

负责核心的字幕生成逻辑、质量检查和重试机制
"""

import os
from typing import Dict, Any, Optional, Callable, List

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings
from .audio_processor import AudioProcessor
from .whisper_model_manager import WhisperModelManager
from .subtitle_file_handler import SubtitleFileHandler


class SubtitleGenerator:
    """字幕生成器"""
    
    def __init__(self):
        """初始化字幕生成器"""
        self.audio_processor = AudioProcessor()
        self.model_manager = WhisperModelManager()
        self.file_handler = SubtitleFileHandler()
        logger.info("字幕生成器初始化完成")
    
    async def generate_from_video(self, 
                                video_path: str,
                                language: str = "auto",
                                model_size: str = None,
                                progress_callback: Optional[Callable] = None,
                                video_title: str = None) -> Dict[str, Any]:
        """
        从视频文件生成字幕
        
        Args:
            video_path: 视频文件路径
            language: 语言代码
            model_size: 模型大小
            progress_callback: 进度回调函数
            video_title: 视频标题
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            if not os.path.exists(video_path):
                raise Exception("视频文件不存在")
            
            # 辅助函数：智能调用progress_callback
            async def safe_progress_callback(progress, message=""):
                if progress_callback:
                    import inspect
                    
                    # 检查是否是协程函数
                    if inspect.iscoroutinefunction(progress_callback):
                        await progress_callback(progress, message)
                    else:
                        progress_callback(progress, message)
            
            # 更新进度
            await safe_progress_callback(5, "正在提取音频...")
            
            # 提取音频
            audio_path = await self.audio_processor.extract_audio(video_path)
            
            await safe_progress_callback(20, "正在加载AI模型...")
            
            # 加载Whisper模型
            model = self.model_manager.load_model(model_size)
            
            await safe_progress_callback(30, "正在生成字幕...")
            
            # 生成字幕
            result = await self._transcribe_audio(
                model, 
                audio_path, 
                language, 
                model_size or settings.WHISPER_MODEL_SIZE,
                safe_progress_callback
            )
            
            if not result["success"]:
                return result
            
            await safe_progress_callback(80, "正在保存字幕文件...")
            
            # 保存字幕
            subtitle_file = await self.file_handler.save_subtitles_from_segments(
                result["segments"], 
                video_title
            )
            
            # 清理临时音频文件
            self.audio_processor.cleanup_temp_audio(audio_path)
            
            await safe_progress_callback(100, "字幕生成完成")
            
            return {
                "success": True,
                "subtitle_file": subtitle_file,
                "language": result["language"],
                "language_probability": result["language_probability"],
                "duration": result["duration"],
                "segments_count": result["segments_count"],
                "model_used": result["model_used"],
                "quality_score": result["quality_score"]
            }
            
        except Exception as e:
            logger.error(f"从视频生成字幕失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_from_audio(self,
                                audio_path: str,
                                language: str = "auto", 
                                model_size: str = None,
                                progress_callback: Optional[Callable] = None,
                                audio_title: str = None) -> Dict[str, Any]:
        """
        从音频文件生成字幕
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            model_size: 模型大小
            progress_callback: 进度回调函数
            audio_title: 音频标题
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            if not os.path.exists(audio_path):
                raise Exception("音频文件不存在")
            
            # 辅助函数：智能调用progress_callback
            async def safe_progress_callback(progress, message=""):
                if progress_callback:
                    import inspect
                    
                    if inspect.iscoroutinefunction(progress_callback):
                        await progress_callback(progress, message)
                    else:
                        progress_callback(progress, message)
            
            await safe_progress_callback(20, "正在加载AI模型...")
            
            # 加载Whisper模型
            model = self.model_manager.load_model(model_size)
            
            await safe_progress_callback(30, "正在生成字幕...")
            
            # 生成字幕
            result = await self._transcribe_audio(
                model,
                audio_path,
                language,
                model_size or settings.WHISPER_MODEL_SIZE,
                safe_progress_callback
            )
            
            if not result["success"]:
                return result
            
            await safe_progress_callback(80, "正在保存字幕文件...")
            
            # 保存字幕
            subtitle_file = await self.file_handler.save_subtitles_from_segments(
                result["segments"],
                audio_title
            )
            
            await safe_progress_callback(100, "字幕生成完成")
            
            return {
                "success": True,
                "subtitle_file": subtitle_file,
                "language": result["language"],
                "language_probability": result["language_probability"],
                "duration": result["duration"],
                "segments_count": result["segments_count"],
                "model_used": result["model_used"],
                "quality_score": result["quality_score"]
            }
            
        except Exception as e:
            logger.error(f"从音频生成字幕失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _transcribe_audio(self,
                              model,
                              audio_path: str,
                              language: str,
                              model_size: str,
                              progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            model: Whisper模型实例
            audio_path: 音频文件路径
            language: 语言代码
            model_size: 模型大小
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 转录结果
        """
        try:
            # 获取模型特定的转录选项
            transcribe_options = self.model_manager.get_model_specific_options(model_size, language)
            
            # 生成字幕
            segments, info = model.transcribe(audio_path, **transcribe_options)
            
            if progress_callback:
                await progress_callback(60, "正在处理转录结果...")
            
            # 流式处理segments，避免阻塞
            segments_list = []
            segment_count = 0
            
            logger.info("开始流式处理转录segments...")
            
            try:
                for i, segment in enumerate(segments):
                    segments_list.append(segment)
                    segment_count += 1
                    
                    # 增加日志输出频率，每10个segments更新一次进度
                    if segment_count % 10 == 0:
                        progress = 60 + min(10, segment_count / 50)  # 60-70%的进度范围
                        if progress_callback:
                            await progress_callback(progress, f"已处理 {segment_count} 个转录段落...")
                        logger.info(f"已处理 {segment_count} 个转录段落")
                    
                    # 每处理5个segments就让出控制权，避免阻塞事件循环
                    if segment_count % 5 == 0:
                        import asyncio
                        await asyncio.sleep(0.001)  # 让出控制权
                        
                logger.info(f"转录结果处理完成，共生成 {segment_count} 个段落")
                
            except Exception as e:
                logger.error(f"处理转录segments失败: {e}")
                # 如果流式处理失败，回退到同步方式
                logger.info("回退到同步处理方式...")
                segments_list = list(segments)
            
            # 检查字幕质量
            quality_check = self._check_subtitle_quality(segments_list, info, model_size)
            if not quality_check["valid"]:
                logger.warning(f"字幕质量检查未通过: {quality_check['reason']}")
                
                # 尝试使用备用参数重新生成
                if quality_check["retry_suggested"]:
                    logger.info("尝试使用备用参数重新生成字幕...")
                    if progress_callback:
                        await progress_callback(35, "字幕质量不佳，正在重新生成...")
                    
                    retry_options = self.model_manager.get_retry_options(model_size, language)
                    segments, info = model.transcribe(audio_path, **retry_options)
                    
                    # 流式处理重试的segments
                    segments_list = []
                    retry_segment_count = 0
                    
                    logger.info("开始流式处理重试转录segments...")
                    
                    try:
                        for segment in segments:
                            segments_list.append(segment)
                            retry_segment_count += 1
                            
                            # 每处理50个segments更新一次进度和让出控制权
                            if retry_segment_count % 50 == 0:
                                if progress_callback:
                                    await progress_callback(45, f"重试处理中... {retry_segment_count} 个段落")
                                import asyncio
                                await asyncio.sleep(0.001)
                                
                        logger.info(f"重试转录结果处理完成，共生成 {retry_segment_count} 个段落")
                        
                    except Exception as e:
                        logger.error(f"重试处理转录segments失败: {e}")
                        segments_list = list(segments)
                    
                    # 再次检查质量
                    retry_quality_check = self._check_subtitle_quality(segments_list, info, model_size)
                    if not retry_quality_check["valid"]:
                        logger.warning(f"重试后字幕质量仍然不佳: {retry_quality_check['reason']}")
            
            if progress_callback:
                await progress_callback(70, "字幕质量检查完成...")
            
            return {
                "success": True,
                "segments": segments_list,
                "language": info.language,
                "language_probability": getattr(info, 'language_probability', 0.0),
                "duration": info.duration,
                "segments_count": len(segments_list),
                "model_used": model_size,
                "quality_score": self._calculate_quality_score(segments_list, info)
            }
            
        except Exception as e:
            logger.error(f"音频转录失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_subtitle_quality(self, segments_list: list, info, model_size: str) -> dict:
        """
        检查字幕质量
        
        Args:
            segments_list: 转录段落列表
            info: 转录信息
            model_size: 模型大小
            
        Returns:
            dict: 质量检查结果
        """
        if not segments_list:
            return {
                "valid": False,
                "reason": "没有生成任何字幕段落",
                "retry_suggested": True
            }
        
        # 检查总文本长度
        total_text = " ".join([segment.text.strip() for segment in segments_list])
        total_length = len(total_text.strip())
        
        if total_length == 0:
            return {
                "valid": False,
                "reason": "生成的字幕为空",
                "retry_suggested": True
            }
        
        if total_length < 10:
            return {
                "valid": False,
                "reason": f"生成的字幕过短({total_length}字符)",
                "retry_suggested": True
            }
        
        # 检查语言检测置信度
        language_probability = getattr(info, 'language_probability', 0.0)
        
        # 对于tiny模型，降低置信度要求
        min_confidence = 0.2 if "tiny" in model_size else 0.3
        
        if language_probability < min_confidence:
            return {
                "valid": False,
                "reason": f"语言检测置信度过低({language_probability:.2f})",
                "retry_suggested": True
            }
        
        # 检查段落数量与音频时长的比例
        duration = info.duration
        segments_count = len(segments_list)
        segments_per_minute = segments_count / (duration / 60) if duration > 0 else 0
        
        # 合理的段落密度：每分钟1-30个段落
        if segments_per_minute > 50:  # 过于密集
            return {
                "valid": False,
                "reason": f"字幕段落过于密集({segments_per_minute:.1f}/分钟)",
                "retry_suggested": True
            }
        
        if duration > 30 and segments_per_minute < 0.5:  # 过于稀疏（仅对长音频检查）
            return {
                "valid": False,
                "reason": f"字幕段落过于稀疏({segments_per_minute:.1f}/分钟)",
                "retry_suggested": True
            }
        
        # 检查是否有异常长的段落
        long_segments = [seg for seg in segments_list if len(seg.text) > 500]
        if len(long_segments) > segments_count * 0.1:  # 超过10%的段落过长
            return {
                "valid": False,
                "reason": f"包含过多异常长的段落({len(long_segments)}个)",
                "retry_suggested": True
            }
        
        return {
            "valid": True,
            "reason": "字幕质量检查通过",
            "retry_suggested": False
        }
    
    def _calculate_quality_score(self, segments_list: list, info) -> float:
        """
        计算字幕质量分数
        
        Args:
            segments_list: 转录段落列表
            info: 转录信息
            
        Returns:
            float: 质量分数 (0-100)
        """
        try:
            if not segments_list or not info:
                return 0.0
            
            score = 0.0
            
            # 语言检测置信度 (40分)
            language_probability = getattr(info, 'language_probability', 0.0)
            score += language_probability * 40
            
            # 文本长度合理性 (20分)
            total_text = " ".join([segment.text.strip() for segment in segments_list])
            text_length = len(total_text)
            duration = info.duration
            
            # 合理的字符数：每分钟50-300字符
            chars_per_minute = text_length / (duration / 60) if duration > 0 else 0
            if 50 <= chars_per_minute <= 300:
                score += 20
            elif 30 <= chars_per_minute <= 500:
                score += 15
            else:
                score += 5
            
            # 段落密度合理性 (20分)
            segments_count = len(segments_list)
            segments_per_minute = segments_count / (duration / 60) if duration > 0 else 0
            if 1 <= segments_per_minute <= 30:
                score += 20
            elif 0.5 <= segments_per_minute <= 50:
                score += 15
            else:
                score += 5
            
            # 段落时长分布 (20分)
            segment_durations = [seg.end - seg.start for seg in segments_list]
            avg_duration = sum(segment_durations) / len(segment_durations)
            
            # 合理的平均段落时长：1-10秒
            if 1.0 <= avg_duration <= 10.0:
                score += 20
            elif 0.5 <= avg_duration <= 15.0:
                score += 15
            else:
                score += 5
            
            return min(100.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"计算质量分数失败: {e}")
            return 50.0  # 默认中等分数
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """获取生成统计信息"""
        return {
            "model_cache": self.model_manager.get_cache_status(),
            "supported_audio_formats": self.audio_processor.supported_audio_formats,
            "supported_video_formats": self.audio_processor.supported_video_formats,
            "supported_subtitle_formats": self.file_handler.get_supported_formats()
        } 
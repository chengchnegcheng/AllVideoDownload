"""
增强字幕文件处理器

优化功能：
- 支持更多字幕格式 (SRT, VTT, ASS, SSA, LRC, SBV)
- 智能字幕校正和优化
- 字幕样式和特效支持
- 批量处理优化
- 字幕质量检测
- 自动时间轴调整
"""

import os
import re
import json
import uuid
import asyncio
import aiofiles
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
from dataclasses import dataclass
from datetime import timedelta
import xml.etree.ElementTree as ET

from ..config import settings
from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SubtitleSegment:
    """字幕段落数据类"""
    index: int
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None
    confidence: Optional[float] = None
    style: Optional[Dict[str, Any]] = None
    
    def duration(self) -> float:
        """获取段落时长"""
        return self.end_time - self.start_time
    
    def words_per_minute(self) -> float:
        """计算语速（词/分钟）"""
        word_count = len(self.text.split())
        duration_minutes = self.duration() / 60
        return word_count / duration_minutes if duration_minutes > 0 else 0


@dataclass
class SubtitleStyle:
    """字幕样式"""
    font_name: str = "Arial"
    font_size: int = 16
    primary_color: str = "&H00FFFFFF"  # 白色
    secondary_color: str = "&H000000FF"  # 红色
    outline_color: str = "&H00000000"  # 黑色
    back_color: str = "&H80000000"  # 半透明黑色
    bold: bool = False
    italic: bool = False
    underline: bool = False
    border_style: int = 1
    outline: int = 2
    shadow: int = 2
    alignment: int = 2  # 底部居中
    margin_left: int = 10
    margin_right: int = 10
    margin_vertical: int = 10


class SubtitleValidator:
    """字幕验证器"""
    
    @staticmethod
    def validate_segments(segments: List[SubtitleSegment]) -> Dict[str, Any]:
        """
        验证字幕段落
        
        Args:
            segments: 字幕段落列表
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        issues = []
        stats = {
            'total_segments': len(segments),
            'total_duration': 0,
            'avg_duration': 0,
            'avg_words_per_minute': 0,
            'overlapping_segments': 0,
            'too_short_segments': 0,
            'too_long_segments': 0
        }
        
        if not segments:
            return {'valid': False, 'issues': ['字幕为空'], 'stats': stats}
        
        # 计算统计信息
        total_duration = 0
        total_wpm = 0
        
        for i, segment in enumerate(segments):
            duration = segment.duration()
            total_duration += duration
            total_wpm += segment.words_per_minute()
            
            # 检查时长
            if duration < 0.5:
                stats['too_short_segments'] += 1
                issues.append(f"段落 {i+1} 时长过短: {duration:.2f}s")
            elif duration > 15:
                stats['too_long_segments'] += 1
                issues.append(f"段落 {i+1} 时长过长: {duration:.2f}s")
            
            # 检查重叠
            if i > 0 and segment.start_time < segments[i-1].end_time:
                stats['overlapping_segments'] += 1
                issues.append(f"段落 {i+1} 与前一段落重叠")
            
            # 检查文本
            if not segment.text.strip():
                issues.append(f"段落 {i+1} 文本为空")
        
        stats['total_duration'] = total_duration
        stats['avg_duration'] = total_duration / len(segments)
        stats['avg_words_per_minute'] = total_wpm / len(segments)
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'stats': stats
        }


class SubtitleOptimizer:
    """字幕优化器"""
    
    @staticmethod
    def optimize_segments(segments: List[SubtitleSegment], 
                         min_duration: float = 1.0,
                         max_duration: float = 10.0,
                         max_chars_per_line: int = 42) -> List[SubtitleSegment]:
        """
        优化字幕段落
        
        Args:
            segments: 原始字幕段落
            min_duration: 最小时长
            max_duration: 最大时长
            max_chars_per_line: 每行最大字符数
            
        Returns:
            List[SubtitleSegment]: 优化后的字幕段落
        """
        optimized = []
        
        for segment in segments:
            # 调整时长
            duration = segment.duration()
            if duration < min_duration:
                # 延长时长
                end_time = segment.start_time + min_duration
                segment.end_time = end_time
            elif duration > max_duration:
                # 缩短时长或分割
                if len(segment.text) > max_chars_per_line * 2:
                    # 分割长字幕
                    split_segments = SubtitleOptimizer._split_long_segment(
                        segment, max_duration, max_chars_per_line
                    )
                    optimized.extend(split_segments)
                    continue
                else:
                    segment.end_time = segment.start_time + max_duration
            
            # 优化文本格式
            segment.text = SubtitleOptimizer._optimize_text(segment.text, max_chars_per_line)
            optimized.append(segment)
        
        return optimized
    
    @staticmethod
    def _split_long_segment(segment: SubtitleSegment, 
                          max_duration: float, 
                          max_chars_per_line: int) -> List[SubtitleSegment]:
        """分割长字幕段落"""
        words = segment.text.split()
        if len(words) <= 1:
            return [segment]
        
        # 尝试在句号、问号、感叹号处分割
        sentences = re.split(r'[.!?。！？]', segment.text)
        if len(sentences) > 1:
            segments = []
            time_per_char = segment.duration() / len(segment.text)
            current_start = segment.start_time
            
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    duration = len(sentence) * time_per_char
                    segments.append(SubtitleSegment(
                        index=segment.index + i,
                        start_time=current_start,
                        end_time=current_start + duration,
                        text=sentence.strip(),
                        speaker=segment.speaker,
                        confidence=segment.confidence
                    ))
                    current_start += duration
            
            return segments
        
        # 按单词分割
        mid_point = len(words) // 2
        first_half = ' '.join(words[:mid_point])
        second_half = ' '.join(words[mid_point:])
        
        mid_time = segment.start_time + segment.duration() / 2
        
        return [
            SubtitleSegment(
                index=segment.index,
                start_time=segment.start_time,
                end_time=mid_time,
                text=first_half,
                speaker=segment.speaker,
                confidence=segment.confidence
            ),
            SubtitleSegment(
                index=segment.index + 1,
                start_time=mid_time,
                end_time=segment.end_time,
                text=second_half,
                speaker=segment.speaker,
                confidence=segment.confidence
            )
        ]
    
    @staticmethod
    def _optimize_text(text: str, max_chars_per_line: int) -> str:
        """优化文本格式"""
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 如果文本不长，直接返回
        if len(text) <= max_chars_per_line:
            return text
        
        # 尝试在合适位置换行
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars_per_line:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)


class EnhancedSubtitleFileHandler:
    """增强字幕文件处理器"""
    
    def __init__(self):
        """初始化增强字幕文件处理器"""
        self.supported_formats = ['.srt', '.vtt', '.ass', '.ssa', '.lrc', '.sbv', '.ttml']
        self.validator = SubtitleValidator()
        self.optimizer = SubtitleOptimizer()
        
        logger.info("增强字幕文件处理器初始化完成")
    
    def sanitize_filename(self, filename: str, max_length: int = 200) -> str:
        """清理文件名"""
        if not filename:
            return "subtitle"
        
        # 移除特殊字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[^\w\s\-_\.]', '_', filename)
        filename = re.sub(r'[_\s]+', '_', filename).strip('_.')
        
        if len(filename) > max_length:
            filename = filename[:max_length].rsplit('_', 1)[0]
        
        return filename if filename else "subtitle"
    
    def format_timestamp(self, seconds: float, format_type: str = "srt") -> str:
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        if format_type.lower() == "srt":
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        elif format_type.lower() == "vtt":
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        elif format_type.lower() in ["ass", "ssa"]:
            centisecs = int((seconds % 1) * 100)
            return f"{hours:01d}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
        elif format_type.lower() == "lrc":
            return f"[{minutes:02d}:{secs:02d}.{millis//10:02d}]"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    async def save_subtitles_enhanced(self, segments: List[SubtitleSegment], 
                                    output_path: str,
                                    format_type: str = "srt",
                                    style: Optional[SubtitleStyle] = None,
                                    optimize: bool = True) -> Dict[str, Any]:
        """
        保存增强字幕文件
        
        Args:
            segments: 字幕段落列表
            output_path: 输出文件路径
            format_type: 字幕格式
            style: 字幕样式
            optimize: 是否优化字幕
            
        Returns:
            Dict[str, Any]: 保存结果
        """
        try:
            # 优化字幕
            if optimize:
                segments = self.optimizer.optimize_segments(segments)
            
            # 验证字幕
            validation_result = self.validator.validate_segments(segments)
            
            # 根据格式保存
            if format_type.lower() == "srt":
                await self._save_srt_enhanced(segments, output_path)
            elif format_type.lower() == "vtt":
                await self._save_vtt_enhanced(segments, output_path)
            elif format_type.lower() in ["ass", "ssa"]:
                await self._save_ass_enhanced(segments, output_path, style)
            elif format_type.lower() == "lrc":
                await self._save_lrc_enhanced(segments, output_path)
            elif format_type.lower() == "sbv":
                await self._save_sbv_enhanced(segments, output_path)
            elif format_type.lower() == "ttml":
                await self._save_ttml_enhanced(segments, output_path)
            else:
                raise ValueError(f"不支持的字幕格式: {format_type}")
            
            return {
                'success': True,
                'output_path': output_path,
                'format': format_type,
                'segments_count': len(segments),
                'validation': validation_result,
                'file_size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"保存增强字幕失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _save_srt_enhanced(self, segments: List[SubtitleSegment], output_path: str):
        """保存SRT格式字幕"""
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start_time = self.format_timestamp(segment.start_time, "srt")
                end_time = self.format_timestamp(segment.end_time, "srt")
                
                await f.write(f"{i}\n")
                await f.write(f"{start_time} --> {end_time}\n")
                await f.write(f"{segment.text}\n\n")
    
    async def _save_vtt_enhanced(self, segments: List[SubtitleSegment], output_path: str):
        """保存VTT格式字幕"""
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write("WEBVTT\n\n")
            
            for segment in segments:
                start_time = self.format_timestamp(segment.start_time, "vtt")
                end_time = self.format_timestamp(segment.end_time, "vtt")
                
                await f.write(f"{start_time} --> {end_time}\n")
                await f.write(f"{segment.text}\n\n")
    
    async def _save_ass_enhanced(self, segments: List[SubtitleSegment], 
                               output_path: str, style: Optional[SubtitleStyle] = None):
        """保存ASS格式字幕"""
        if not style:
            style = SubtitleStyle()
        
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            # 写入头部
            await f.write("[Script Info]\n")
            await f.write("Title: Generated by AVD\n")
            await f.write("ScriptType: v4.00+\n\n")
            
            # 写入样式
            await f.write("[V4+ Styles]\n")
            await f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            
            style_line = (
                f"Style: Default,{style.font_name},{style.font_size},"
                f"{style.primary_color},{style.secondary_color},{style.outline_color},{style.back_color},"
                f"{-1 if style.bold else 0},{-1 if style.italic else 0},{-1 if style.underline else 0},0,"
                f"100,100,0,0,{style.border_style},{style.outline},{style.shadow},"
                f"{style.alignment},{style.margin_left},{style.margin_right},{style.margin_vertical},1\n\n"
            )
            await f.write(style_line)
            
            # 写入事件
            await f.write("[Events]\n")
            await f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            for segment in segments:
                start_time = self.format_timestamp(segment.start_time, "ass")
                end_time = self.format_timestamp(segment.end_time, "ass")
                text = segment.text.replace('\n', '\\N')
                
                await f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
    
    async def _save_lrc_enhanced(self, segments: List[SubtitleSegment], output_path: str):
        """保存LRC格式字幕"""
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write("[ti:Generated by AVD]\n")
            await f.write("[ar:Unknown]\n")
            await f.write("[al:Unknown]\n\n")
            
            for segment in segments:
                timestamp = self.format_timestamp(segment.start_time, "lrc")
                text = segment.text.replace('\n', ' ')
                await f.write(f"{timestamp}{text}\n")
    
    async def _save_sbv_enhanced(self, segments: List[SubtitleSegment], output_path: str):
        """保存SBV格式字幕"""
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                start_time = self.format_timestamp(segment.start_time, "srt").replace(',', '.')
                end_time = self.format_timestamp(segment.end_time, "srt").replace(',', '.')
                
                await f.write(f"{start_time},{end_time}\n")
                await f.write(f"{segment.text}\n\n")
    
    async def _save_ttml_enhanced(self, segments: List[SubtitleSegment], output_path: str):
        """保存TTML格式字幕"""
        root = ET.Element("tt")
        root.set("xmlns", "http://www.w3.org/ns/ttml")
        root.set("xmlns:tts", "http://www.w3.org/ns/ttml#styling")
        
        head = ET.SubElement(root, "head")
        styling = ET.SubElement(head, "styling")
        style = ET.SubElement(styling, "style")
        style.set("xml:id", "defaultStyle")
        style.set("tts:fontSize", "16px")
        style.set("tts:color", "white")
        
        body = ET.SubElement(root, "body")
        div = ET.SubElement(body, "div")
        
        for segment in segments:
            p = ET.SubElement(div, "p")
            p.set("begin", f"{segment.start_time:.3f}s")
            p.set("end", f"{segment.end_time:.3f}s")
            p.set("style", "defaultStyle")
            p.text = segment.text
        
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    async def convert_format_enhanced(self, input_path: str, 
                                    output_format: str,
                                    output_path: str = None,
                                    style: Optional[SubtitleStyle] = None) -> Dict[str, Any]:
        """
        增强字幕格式转换
        
        Args:
            input_path: 输入文件路径
            output_format: 目标格式
            output_path: 输出文件路径
            style: 字幕样式
            
        Returns:
            Dict[str, Any]: 转换结果
        """
        try:
            # 读取原始字幕
            segments = await self._parse_subtitle_file(input_path)
            
            if not segments:
                raise ValueError("无法解析输入字幕文件")
            
            # 生成输出路径
            if not output_path:
                input_name = Path(input_path).stem
                output_path = os.path.join(
                    os.path.dirname(input_path),
                    f"{input_name}.{output_format}"
                )
            
            # 保存为目标格式
            result = await self.save_subtitles_enhanced(
                segments, output_path, output_format, style
            )
            
            return result
            
        except Exception as e:
            logger.error(f"字幕格式转换失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _parse_subtitle_file(self, file_path: str) -> List[SubtitleSegment]:
        """解析字幕文件"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.srt':
            return await self._parse_srt_file(file_path)
        elif file_ext == '.vtt':
            return await self._parse_vtt_file(file_path)
        elif file_ext in ['.ass', '.ssa']:
            return await self._parse_ass_file(file_path)
        elif file_ext == '.lrc':
            return await self._parse_lrc_file(file_path)
        else:
            raise ValueError(f"不支持的字幕格式: {file_ext}")
    
    async def _parse_srt_file(self, file_path: str) -> List[SubtitleSegment]:
        """解析SRT文件"""
        segments = []
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                index = int(lines[0])
                timestamp = lines[1]
                text = '\n'.join(lines[2:])
                
                if ' --> ' in timestamp:
                    start_str, end_str = timestamp.split(' --> ')
                    start_time = self._parse_timestamp(start_str.strip())
                    end_time = self._parse_timestamp(end_str.strip())
                    
                    segments.append(SubtitleSegment(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        text=text.strip()
                    ))
        
        return segments
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """解析时间戳为秒数"""
        try:
            # 支持多种格式
            if ',' in timestamp:
                time_part, millis = timestamp.split(',')
            elif '.' in timestamp:
                time_part, millis = timestamp.rsplit('.', 1)
            else:
                time_part = timestamp
                millis = "0"
            
            time_components = time_part.split(':')
            if len(time_components) == 3:
                hours, minutes, seconds = map(int, time_components)
            elif len(time_components) == 2:
                hours = 0
                minutes, seconds = map(int, time_components)
            else:
                return 0.0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            if millis:
                if len(millis) == 1:
                    millis += "00"
                elif len(millis) == 2:
                    millis += "0"
                elif len(millis) > 3:
                    millis = millis[:3]
                
                total_seconds += int(millis) / 1000.0
            
            return total_seconds
            
        except Exception as e:
            logger.error(f"解析时间戳失败: {timestamp}, 错误: {e}")
            return 0.0
    
    async def save_subtitles_from_segments(self, segments, 
                                         video_title: str = None, 
                                         format_type: str = "srt") -> str:
        """
        从Whisper segments保存字幕文件 (兼容接口)
        
        Args:
            segments: Whisper转录的segments
            video_title: 视频标题
            format_type: 字幕格式
            
        Returns:
            str: 保存的字幕文件路径
        """
        try:
            # 转换为SubtitleSegment格式
            subtitle_segments = []
            for i, segment in enumerate(segments, 1):
                subtitle_segments.append(SubtitleSegment(
                    index=i,
                    start_time=segment.start,
                    end_time=segment.end,
                    text=segment.text.strip()
                ))
            
            # 生成文件名
            if video_title:
                safe_title = self.sanitize_filename(video_title)
                subtitle_filename = f"{safe_title}_subtitles.{format_type}"
            else:
                subtitle_filename = f"{uuid.uuid4()}_subtitles.{format_type}"
            
            subtitle_path = os.path.join(settings.FILES_PATH, subtitle_filename)
            
            # 保存字幕
            result = await self.save_subtitles_enhanced(
                subtitle_segments, subtitle_path, format_type
            )
            
            if result['success']:
                logger.info(f"字幕文件保存成功: {subtitle_path}")
                return subtitle_path
            else:
                raise Exception(result.get('error', '保存失败'))
            
        except Exception as e:
            logger.error(f"保存字幕失败: {e}")
            raise
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        return [fmt[1:] for fmt in self.supported_formats]  # 去掉点号
    
    async def cleanup(self):
        """清理资源"""
        logger.info("增强字幕文件处理器资源已清理")


# 全局实例
_enhanced_file_handler = None

def get_enhanced_subtitle_file_handler() -> EnhancedSubtitleFileHandler:
    """获取增强字幕文件处理器实例"""
    global _enhanced_file_handler
    if _enhanced_file_handler is None:
        _enhanced_file_handler = EnhancedSubtitleFileHandler()
    return _enhanced_file_handler
"""
字幕文件处理器

负责字幕文件的解析、保存、格式转换等功能
"""

import os
import re
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings


class SubtitleFileHandler:
    """字幕文件处理器"""
    
    def __init__(self):
        """初始化字幕文件处理器"""
        self.supported_formats = ['.srt', '.vtt', '.ass', '.ssa', '.sub']
        logger.info("字幕文件处理器初始化完成")
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的字幕格式列表"""
        return self.supported_formats.copy()
    
    def sanitize_filename(self, filename: str, max_length: int = 200, default_name: str = "subtitle") -> str:
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
        
        # 移除或替换非法字符，包括全角字符
        illegal_chars = r'[<>:"/\\|?*｜￤]'  # 添加全角竖线和其他可能的特殊字符
        filename = re.sub(illegal_chars, '_', filename)
        
        # 移除表情符号和其他Unicode特殊字符
        filename = re.sub(r'[^\w\s\-_\.]', '_', filename)
        
        # 移除多余的空格、下划线和点
        filename = re.sub(r'[_\s]+', '_', filename).strip('_.')
        
        # 确保不以点开头或结尾
        filename = filename.strip('.')
        
        # 限制长度
        if len(filename) > max_length:
            filename = filename[:max_length].rsplit('_', 1)[0]
        
        return filename if filename else default_name
    
    def format_timestamp(self, seconds: float, format_type: str = "srt") -> str:
        """
        格式化时间戳
        
        Args:
            seconds: 秒数
            format_type: 格式类型 (srt, vtt, ass)
            
        Returns:
            str: 格式化的时间戳
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        if format_type.lower() == "srt":
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        elif format_type.lower() == "vtt":
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        elif format_type.lower() == "ass":
            centisecs = int((seconds % 1) * 100)
            return f"{hours:01d}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def parse_timestamp(self, timestamp: str) -> float:
        """
        解析时间戳为秒数
        
        Args:
            timestamp: 时间戳字符串
            
        Returns:
            float: 秒数
        """
        try:
            # 支持多种格式: HH:MM:SS,mmm 或 HH:MM:SS.mmm
            if ',' in timestamp:
                time_part, millis = timestamp.split(',')
            elif '.' in timestamp:
                time_part, millis = timestamp.rsplit('.', 1)
            else:
                time_part = timestamp
                millis = "0"
            
            # 解析时分秒
            time_components = time_part.split(':')
            if len(time_components) == 3:
                hours, minutes, seconds = map(int, time_components)
            elif len(time_components) == 2:
                hours = 0
                minutes, seconds = map(int, time_components)
            else:
                return 0.0
            
            # 转换为总秒数
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # 添加毫秒
            if millis:
                # 处理不同精度的毫秒
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
    
    def parse_srt_file(self, srt_path: str) -> List[Dict]:
        """
        解析SRT字幕文件
        
        Args:
            srt_path: SRT文件路径
            
        Returns:
            List[Dict]: 字幕列表
        """
        subtitles = []
        
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 分割字幕块
            blocks = content.split('\n\n')
            
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    index = lines[0].strip()
                    timestamp = lines[1].strip()
                    text = '\n'.join(lines[2:]).strip()
                    
                    # 解析时间戳
                    if ' --> ' in timestamp:
                        start_time_str, end_time_str = timestamp.split(' --> ')
                        start_time = self.parse_timestamp(start_time_str.strip())
                        end_time = self.parse_timestamp(end_time_str.strip())
                        
                        subtitles.append({
                            'index': index,
                            'start_time': start_time_str.strip(),
                            'end_time': end_time_str.strip(),
                            'start_seconds': start_time,
                            'end_seconds': end_time,
                            'text': text
                        })
            
            logger.info(f"成功解析SRT文件: {len(subtitles)}条字幕")
            return subtitles
            
        except Exception as e:
            logger.error(f"解析SRT文件失败: {e}")
            raise
    
    def save_srt_file(self, subtitles: List[Dict], output_path: str):
        """
        保存SRT字幕文件
        
        Args:
            subtitles: 字幕列表
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for subtitle in subtitles:
                    f.write(f"{subtitle['index']}\n")
                    f.write(f"{subtitle['start_time']} --> {subtitle['end_time']}\n")
                    f.write(f"{subtitle['text']}\n\n")
            
            logger.info(f"SRT文件保存成功: {output_path}")
            
        except Exception as e:
            logger.error(f"保存SRT文件失败: {e}")
            raise
    
    def save_vtt_file(self, subtitles: List[Dict], output_path: str):
        """
        保存VTT字幕文件
        
        Args:
            subtitles: 字幕列表
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                
                for subtitle in subtitles:
                    # 转换时间戳格式
                    start_time = self.format_timestamp(subtitle.get('start_seconds', 0), "vtt")
                    end_time = self.format_timestamp(subtitle.get('end_seconds', 0), "vtt")
                    
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{subtitle['text']}\n\n")
            
            logger.info(f"VTT文件保存成功: {output_path}")
            
        except Exception as e:
            logger.error(f"保存VTT文件失败: {e}")
            raise
    
    async def save_subtitles_from_segments(self, segments, video_title: str = None, format_type: str = "srt") -> str:
        """
        从Whisper segments保存字幕文件
        
        Args:
            segments: Whisper转录的segments
            video_title: 视频标题
            format_type: 字幕格式
            
        Returns:
            str: 保存的字幕文件路径
        """
        try:
            # 生成字幕文件名
            if video_title:
                safe_title = self.sanitize_filename(video_title)
                subtitle_filename = f"{safe_title}_subtitles.{format_type}"
            else:
                subtitle_filename = f"{uuid.uuid4()}_subtitles.{format_type}"
            
            subtitle_path = os.path.join(settings.FILES_PATH, subtitle_filename)
            
            # 转换segments为字幕条目
            subtitles = []
            for i, segment in enumerate(segments, 1):
                start_time_str = self.format_timestamp(segment.start, format_type)
                end_time_str = self.format_timestamp(segment.end, format_type)
                text = segment.text.strip()
                
                subtitles.append({
                    'index': str(i),
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'start_seconds': segment.start,
                    'end_seconds': segment.end,
                    'text': text
                })
            
            # 根据格式保存文件
            if format_type.lower() == "srt":
                self.save_srt_file(subtitles, subtitle_path)
            elif format_type.lower() == "vtt":
                self.save_vtt_file(subtitles, subtitle_path)
            else:
                # 默认保存为SRT
                self.save_srt_file(subtitles, subtitle_path)
            
            logger.info(f"字幕文件保存成功: {subtitle_path}")
            return subtitle_path
            
        except Exception as e:
            logger.error(f"保存字幕失败: {e}")
            raise
    
    def convert_format(self, input_path: str, output_format: str, output_path: str = None) -> str:
        """
        转换字幕格式
        
        Args:
            input_path: 输入文件路径
            output_format: 目标格式 (srt, vtt等)
            output_path: 输出文件路径（可选）
            
        Returns:
            str: 输出文件路径
        """
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"输入文件不存在: {input_path}")
            
            # 解析输入文件
            input_ext = Path(input_path).suffix.lower()
            if input_ext == '.srt':
                subtitles = self.parse_srt_file(input_path)
            else:
                raise ValueError(f"暂不支持转换格式: {input_ext}")
            
            # 生成输出文件路径
            if not output_path:
                input_name = Path(input_path).stem
                output_path = os.path.join(
                    os.path.dirname(input_path),
                    f"{input_name}.{output_format}"
                )
            
            # 保存为目标格式
            if output_format.lower() == "srt":
                self.save_srt_file(subtitles, output_path)
            elif output_format.lower() == "vtt":
                self.save_vtt_file(subtitles, output_path)
            else:
                raise ValueError(f"暂不支持目标格式: {output_format}")
            
            logger.info(f"字幕格式转换成功: {input_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"字幕格式转换失败: {e}")
            raise
    
    def validate_subtitle_file(self, file_path: str) -> Dict[str, Any]:
        """
        验证字幕文件
        
        Args:
            file_path: 字幕文件路径
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            if not os.path.exists(file_path):
                return {
                    "valid": False,
                    "error": "文件不存在"
                }
            
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                return {
                    "valid": False,
                    "error": f"不支持的文件格式: {file_ext}"
                }
            
            # 尝试解析文件
            if file_ext == '.srt':
                subtitles = self.parse_srt_file(file_path)
                
                if not subtitles:
                    return {
                        "valid": False,
                        "error": "字幕文件为空"
                    }
                
                # 检查时间戳合理性
                invalid_timestamps = 0
                for subtitle in subtitles:
                    if subtitle.get('start_seconds', 0) >= subtitle.get('end_seconds', 0):
                        invalid_timestamps += 1
                
                return {
                    "valid": True,
                    "format": file_ext[1:],  # 去掉点
                    "count": len(subtitles),
                    "invalid_timestamps": invalid_timestamps,
                    "file_size": os.path.getsize(file_path)
                }
            else:
                # 其他格式的基本验证
                file_size = os.path.getsize(file_path)
                return {
                    "valid": True,
                    "format": file_ext[1:],
                    "file_size": file_size
                }
                
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def get_subtitle_stats(self, file_path: str) -> Dict[str, Any]:
        """
        获取字幕文件统计信息
        
        Args:
            file_path: 字幕文件路径
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            if Path(file_path).suffix.lower() == '.srt':
                subtitles = self.parse_srt_file(file_path)
                
                if not subtitles:
                    return {"error": "字幕文件为空"}
                
                # 计算统计信息
                total_duration = subtitles[-1].get('end_seconds', 0) - subtitles[0].get('start_seconds', 0)
                total_chars = sum(len(sub['text']) for sub in subtitles)
                avg_duration = total_duration / len(subtitles) if len(subtitles) > 0 else 0
                
                return {
                    "total_subtitles": len(subtitles),
                    "total_duration": total_duration,
                    "total_characters": total_chars,
                    "average_duration_per_subtitle": avg_duration,
                    "characters_per_second": total_chars / total_duration if total_duration > 0 else 0
                }
            else:
                return {"error": "暂不支持此格式的统计"}
                
        except Exception as e:
            logger.error(f"获取字幕统计信息失败: {e}")
            return {"error": str(e)} 
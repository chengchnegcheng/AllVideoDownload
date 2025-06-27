"""
音频处理器模块

负责视频音频提取、音频格式转换等功能
"""

import os
import subprocess
import uuid
from typing import Optional
from pathlib import Path

from ...utils.logger import get_logger
logger = get_logger(__name__)
from ..config import settings


class AudioProcessor:
    """音频处理器"""
    
    def __init__(self):
        """初始化音频处理器"""
        self.supported_video_formats = [
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', 
            '.webm', '.m4v', '.3gp', '.f4v', '.ts', '.mts'
        ]
        self.supported_audio_formats = [
            '.mp3', '.wav', '.aac', '.m4a', '.ogg', '.flac', 
            '.wma', '.opus', '.webm'
        ]
        logger.info("音频处理器初始化完成")
    
    async def extract_audio(self, video_path: str, output_format: str = "wav") -> str:
        """
        从视频中提取音频
        
        Args:
            video_path: 视频文件路径
            output_format: 输出音频格式 (wav, mp3, aac等)
            
        Returns:
            str: 提取的音频文件路径
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            # 检查文件格式
            file_ext = Path(video_path).suffix.lower()
            if file_ext not in self.supported_video_formats and file_ext not in self.supported_audio_formats:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            # 生成输出文件路径
            audio_filename = f"{uuid.uuid4()}.{output_format}"
            audio_path = os.path.join(settings.TEMP_PATH, audio_filename)
            
            # 如果输入文件已经是音频格式，考虑直接复制或转换
            if file_ext in self.supported_audio_formats:
                if file_ext == f".{output_format}":
                    # 格式相同，直接复制
                    import shutil
                    shutil.copy2(video_path, audio_path)
                    logger.info(f"音频文件直接复制: {audio_path}")
                    return audio_path
            
            # 构建ffmpeg命令
            cmd = self._build_ffmpeg_command(video_path, audio_path, output_format)
            
            # 执行ffmpeg命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode != 0:
                raise Exception(f"音频提取失败: {result.stderr}")
            
            # 验证输出文件
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                raise Exception("音频提取失败: 输出文件为空或不存在")
            
            logger.info(f"音频提取成功: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            raise
    
    def _build_ffmpeg_command(self, input_path: str, output_path: str, format: str) -> list:
        """构建ffmpeg命令"""
        cmd = ["ffmpeg", "-i", input_path]
        
        if format.lower() == "wav":
            cmd.extend([
                "-vn",  # 禁用视频
                "-acodec", "pcm_s16le",  # 使用PCM 16位编码
                "-ar", "16000",  # 采样率16kHz (Whisper推荐)
                "-ac", "1",  # 单声道
                "-y",  # 覆盖输出文件
                output_path
            ])
        elif format.lower() == "mp3":
            cmd.extend([
                "-vn", 
                "-acodec", "libmp3lame",
                "-ab", "128k",  # 128kbps比特率
                "-ar", "16000",
                "-ac", "1",
                "-y", 
                output_path
            ])
        elif format.lower() == "aac":
            cmd.extend([
                "-vn",
                "-acodec", "aac",
                "-ab", "128k",
                "-ar", "16000", 
                "-ac", "1",
                "-y",
                output_path
            ])
        else:
            # 默认参数
            cmd.extend([
                "-vn",
                "-ar", "16000",
                "-ac", "1", 
                "-y",
                output_path
            ])
        
        return cmd
    
    async def convert_audio_format(self, input_path: str, output_format: str) -> str:
        """
        转换音频格式
        
        Args:
            input_path: 输入音频文件路径
            output_format: 目标格式
            
        Returns:
            str: 转换后的音频文件路径
        """
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"音频文件不存在: {input_path}")
            
            # 生成输出文件路径
            output_filename = f"{uuid.uuid4()}.{output_format}"
            output_path = os.path.join(settings.TEMP_PATH, output_filename)
            
            # 构建转换命令
            cmd = self._build_ffmpeg_command(input_path, output_path, output_format)
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise Exception(f"音频格式转换失败: {result.stderr}")
            
            logger.info(f"音频格式转换成功: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {e}")
            raise
    
    def get_audio_info(self, audio_path: str) -> dict:
        """
        获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            dict: 音频信息
        """
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", audio_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"获取音频信息失败: {result.stderr}")
            
            import json
            info = json.loads(result.stdout)
            
            # 提取关键信息
            audio_info = {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size": int(info.get("format", {}).get("size", 0)),
                "bit_rate": int(info.get("format", {}).get("bit_rate", 0)),
                "format_name": info.get("format", {}).get("format_name", ""),
                "streams": []
            }
            
            # 提取音频流信息
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_info["streams"].append({
                        "codec_name": stream.get("codec_name", ""),
                        "sample_rate": int(stream.get("sample_rate", 0)),
                        "channels": int(stream.get("channels", 0)),
                        "duration": float(stream.get("duration", 0))
                    })
            
            return audio_info
            
        except Exception as e:
            logger.error(f"获取音频信息失败: {e}")
            return {}
    
    def validate_audio_file(self, audio_path: str) -> bool:
        """
        验证音频文件是否有效
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            bool: 文件是否有效
        """
        try:
            if not os.path.exists(audio_path):
                return False
            
            if os.path.getsize(audio_path) == 0:
                return False
            
            # 获取音频信息来验证文件完整性
            info = self.get_audio_info(audio_path)
            if not info or info.get("duration", 0) <= 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证音频文件失败: {e}")
            return False
    
    def cleanup_temp_audio(self, audio_path: str) -> bool:
        """
        清理临时音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            bool: 清理是否成功
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"临时音频文件已清理: {audio_path}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"清理临时音频文件失败: {e}")
            return False 
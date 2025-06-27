"""
字幕处理模块包

此包包含字幕处理系统的所有组件：
- audio_processor: 音频提取和处理
- whisper_model_manager: Whisper模型管理
- subtitle_translator: 字幕翻译功能
- subtitle_file_handler: 字幕文件处理
- subtitle_generator: 字幕生成核心逻辑
- url_processor: 从URL生成字幕
- subtitle_effects: 字幕特效和烧录
"""

from .audio_processor import AudioProcessor
from .whisper_model_manager import WhisperModelManager
from .subtitle_translator import SubtitleTranslator
from .subtitle_file_handler import SubtitleFileHandler
from .subtitle_generator import SubtitleGenerator
from .url_processor import URLProcessor
from .subtitle_effects import SubtitleEffects

__all__ = [
    'AudioProcessor',
    'WhisperModelManager', 
    'SubtitleTranslator',
    'SubtitleFileHandler',
    'SubtitleGenerator',
    'URLProcessor',
    'SubtitleEffects'
]

__version__ = '1.0.0' 
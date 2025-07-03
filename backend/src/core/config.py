"""
AVD Web版本 - 配置管理模块

统一管理应用配置，支持环境变量和配置文件
"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """应用配置类"""
    
    # 基本配置
    APP_NAME: str = "AVD Web"
    VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # 安全配置
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALLOWED_ORIGINS: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")  # 允许所有来源
    
    # 数据库配置
    DATABASE_URL: str = Field(default="", env="DATABASE_URL")  # 将在__init__中设置绝对路径
    
    # Redis配置（用于任务队列）
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # 文件路径配置
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    FILES_PATH: str = str(DATA_DIR / "files")  # 统一的文件存储路径
    DOWNLOAD_PATH: str = str(DATA_DIR / "files")  # 保持向后兼容
    UPLOAD_PATH: str = str(DATA_DIR / "files")    # 保持向后兼容
    TEMP_PATH: str = str(DATA_DIR / "temp")  # 添加临时文件路径
    MODELS_PATH: str = str(DATA_DIR / "models")
    LOGS_PATH: str = str(BASE_DIR.parent / "logs")  # 指向项目根目录的logs文件夹
    
    # 下载配置
    MAX_CONCURRENT_DOWNLOADS: int = Field(default=3, env="MAX_CONCURRENT_DOWNLOADS")
    MAX_FILE_SIZE_MB: int = Field(default=1024, env="MAX_FILE_SIZE_MB")  # 1GB
    SUPPORTED_FORMATS: List[str] = Field(default=["mp4", "webm", "mkv", "avi", "mov", "mp3", "wav", "m4a"])
    
    # AI模型配置 - 优化为large-v3最高品质无限制模式
    WHISPER_MODEL_SIZE: str = Field(default="large-v3", env="WHISPER_MODEL_SIZE")  # 使用large-v3最高品质模型
    WHISPER_DEVICE: str = Field(default="auto", env="WHISPER_DEVICE")  # 自动检测设备类型
    WHISPER_SOURCE_LANGUAGE: str = Field(default="auto", env="WHISPER_SOURCE_LANGUAGE")  # 源语言设置
    
    # 增强AI设置
    # Whisper模型选项
    WHISPER_AVAILABLE_MODELS: List[str] = Field(default=[
        "tiny", "tiny.en", "base", "base.en", 
        "small", "small.en", "medium", "medium.en", 
        "large", "large-v1", "large-v2", "large-v3"
    ])
    
    # AI性能配置 - 无限制模式，充分利用CPU资源
    AI_AUTO_DEVICE_SELECTION: bool = Field(default=True, env="AI_AUTO_DEVICE_SELECTION")  # 自动选择设备
    AI_MAX_MEMORY_USAGE_MB: int = Field(default=16384, env="AI_MAX_MEMORY_USAGE_MB")  # 增加到16GB充分利用内存
    AI_BATCH_SIZE: int = Field(default=32, env="AI_BATCH_SIZE")  # 增大批处理提高效率
    AI_NUM_WORKERS: int = Field(default=0, env="AI_NUM_WORKERS")  # 设为0表示无限制，使用所有可用CPU核心
    
    # Whisper高级配置 - large-v3最高品质配置
    WHISPER_COMPUTE_TYPE: str = Field(default="int8", env="WHISPER_COMPUTE_TYPE")  # 使用int8获得最佳CPU性能（约4倍速度提升）
    WHISPER_BEAM_SIZE: int = Field(default=5, env="WHISPER_BEAM_SIZE")  # 增加束搜索提高质量
    WHISPER_BEST_OF: int = Field(default=5, env="WHISPER_BEST_OF")  # 增加候选数量提高质量
    WHISPER_PATIENCE: float = Field(default=2.0, env="WHISPER_PATIENCE")  # 增加耐心值提高质量
    WHISPER_SUPPRESS_TOKENS: List[int] = Field(default=[-1], env="WHISPER_SUPPRESS_TOKENS")  # 抑制token
    WHISPER_VAD_FILTER: bool = Field(default=True, env="WHISPER_VAD_FILTER")  # 启用VAD过滤器提高质量
    WHISPER_VAD_THRESHOLD: float = Field(default=0.5, env="WHISPER_VAD_THRESHOLD")  # 适中VAD阈值
    WHISPER_VAD_MIN_SILENCE_DURATION_MS: int = Field(default=2000, env="WHISPER_VAD_MIN_SILENCE_DURATION_MS")  # 适中静音时长
    
    # 模型缓存配置 - 针对large-v3优化
    AI_MODEL_CACHE_SIZE: int = Field(default=3, env="AI_MODEL_CACHE_SIZE")  # 增加缓存模型数量
    AI_MODEL_AUTO_DOWNLOAD: bool = Field(default=True, env="AI_MODEL_AUTO_DOWNLOAD")  # 自动下载模型
    AI_MODEL_DOWNLOAD_TIMEOUT: int = Field(default=1800, env="AI_MODEL_DOWNLOAD_TIMEOUT")  # 增加下载超时到30分钟（Large-v3模型较大）
    
    # 语言检测配置 - 优化检测精度
    AI_AUTO_LANGUAGE_DETECTION: bool = Field(default=True, env="AI_AUTO_LANGUAGE_DETECTION")  # 自动语言检测
    AI_LANGUAGE_DETECTION_THRESHOLD: float = Field(default=0.5, env="AI_LANGUAGE_DETECTION_THRESHOLD")  # 提高语言检测阈值以获得更准确的结果
    
    # 后处理配置 - 优化字幕质量
    AI_SUBTITLE_POST_PROCESSING: bool = Field(default=True, env="AI_SUBTITLE_POST_PROCESSING")  # 字幕后处理
    AI_REMOVE_DUPLICATE_SENTENCES: bool = Field(default=True, env="AI_REMOVE_DUPLICATE_SENTENCES")  # 去重复句子
    AI_SENTENCE_MIN_LENGTH: int = Field(default=3, env="AI_SENTENCE_MIN_LENGTH")  # 降低最小句子长度以保留更多内容
    AI_SENTENCE_MAX_LENGTH: int = Field(default=300, env="AI_SENTENCE_MAX_LENGTH")  # 增加最大句子长度以适应更复杂的句子
    
    # 实验性功能 - 启用一些实用功能
    AI_EXPERIMENTAL_FEATURES: bool = Field(default=True, env="AI_EXPERIMENTAL_FEATURES")  # 启用实验性功能以获得更多特性
    AI_USE_ENHANCED_WHISPER: bool = Field(default=True, env="AI_USE_ENHANCED_WHISPER")  # 启用增强Whisper以获得更好的效果
    AI_SPEAKER_DIARIZATION: bool = Field(default=False, env="AI_SPEAKER_DIARIZATION")  # 说话人分离（保持关闭，消耗资源较多）
    
    # 翻译服务配置
    TRANSLATION_STRATEGY: str = Field(default="local_only", env="TRANSLATION_STRATEGY")  # 仅本地翻译
    
    # 字幕翻译方法配置 - 优化默认配置
    SUBTITLE_TRANSLATION_METHOD: str = Field(default="sentencepiece", env="SUBTITLE_TRANSLATION_METHOD")  # 默认翻译方法
    SUBTITLE_TRANSLATION_TIMEOUT: int = Field(default=300, env="SUBTITLE_TRANSLATION_TIMEOUT")  # 翻译超时时间增加到5分钟
    SUBTITLE_TRANSLATION_MAX_RETRIES: int = Field(default=3, env="SUBTITLE_TRANSLATION_MAX_RETRIES")  # 最大重试次数增加到3次
    SUBTITLE_FALLBACK_ENABLED: bool = Field(default=True, env="SUBTITLE_FALLBACK_ENABLED")  # 启用回退翻译
    SUBTITLE_DEFAULT_TARGET_LANGUAGE: str = Field(default="zh-cn", env="SUBTITLE_DEFAULT_TARGET_LANGUAGE")  # 默认目标语言
    
    # 可用的翻译方法
    AVAILABLE_TRANSLATION_METHODS: List[str] = Field(default=[
        "sentencepiece"      # SentencePiece翻译方法
    ])
    
    # SentencePiece配置 - 优化为更好的默认设置
    SENTENCEPIECE_MODEL_SIZE: str = Field(default="large", env="SENTENCEPIECE_MODEL_SIZE")  # 使用large获得更好的翻译质量
    SENTENCEPIECE_VOCAB_SIZE: int = Field(default=1000, env="SENTENCEPIECE_VOCAB_SIZE")  # 增加词汇表大小提高翻译质量
    
    # 已废弃配置（为兼容性保留）
    TRANSLATION_SERVICE: str = Field(default="local", env="TRANSLATION_SERVICE")  # local 或 online
    
    # 代理配置
    HTTP_PROXY: str = Field(default="", env="HTTP_PROXY")
    HTTPS_PROXY: str = Field(default="", env="HTTPS_PROXY")
    
    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Cookie配置
    COOKIE_STORAGE_PATH: str = str(DATA_DIR / "cookies")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_ROTATION: str = Field(default="1 day", env="LOG_ROTATION")
    LOG_RETENTION: str = Field(default="30 days", env="LOG_RETENTION")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的字段

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 设置数据库URL（如果环境变量未设置）
        if not self.DATABASE_URL:
            db_path = self.DATA_DIR / "avd.db"
            self.DATABASE_URL = f"sqlite:///{db_path}"
        
        # 确保目录存在
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.FILES_PATH).mkdir(parents=True, exist_ok=True)  # 统一的文件目录
        Path(self.DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)  # 向后兼容
        Path(self.UPLOAD_PATH).mkdir(parents=True, exist_ok=True)    # 向后兼容
        Path(self.TEMP_PATH).mkdir(parents=True, exist_ok=True)  # 确保临时目录存在
        Path(self.MODELS_PATH).mkdir(parents=True, exist_ok=True)
        # LOGS_PATH 目录已存在于项目根目录，确保可访问
        Path(self.LOGS_PATH).mkdir(parents=True, exist_ok=True)
        Path(self.COOKIE_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

# 全局配置实例
settings = Settings()

# 平台支持配置
SUPPORTED_PLATFORMS = {
    "youtube": {
        "name": "YouTube",
        "domains": ["youtube.com", "youtu.be", "m.youtube.com"],
        "extractors": ["youtube", "youtube:tab"],
        "requires_cookies": False
    },
    "bilibili": {
        "name": "哔哩哔哩",
        "domains": ["bilibili.com", "b23.tv"],
        "extractors": ["bilibili", "bilibili:bangumi"],
        "requires_cookies": True
    },
    "twitter": {
        "name": "Twitter/X",
        "domains": ["twitter.com", "x.com", "t.co"],
        "extractors": ["twitter"],
        "requires_cookies": True
    },
    "tiktok": {
        "name": "TikTok",
        "domains": ["tiktok.com", "vm.tiktok.com"],
        "extractors": ["tiktok"],
        "requires_cookies": False
    },
    "instagram": {
        "name": "Instagram",
        "domains": ["instagram.com"],
        "extractors": ["instagram"],
        "requires_cookies": True
    },
    "douyin": {
        "name": "抖音",
        "domains": ["douyin.com"],
        "extractors": ["douyin"],
        "requires_cookies": False
    }
}

# 质量选项配置
QUALITY_OPTIONS = {
    "best": "最佳质量",
    "worst": "最低质量",
    "1080p": "1080p高清",
    "720p": "720p高清",
    "480p": "480p标清",
    "360p": "360p流畅",
    "audio_only": "仅音频"
}

# 字幕语言配置
SUBTITLE_LANGUAGES = {
    "auto": "自动检测",
    "zh-cn": "简体中文",
    "zh-tw": "繁体中文",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "ar": "阿拉伯语"
}

# 翻译方法配置
TRANSLATION_METHODS = {
    "sentencepiece": {
        "name": "SentencePiece翻译方法",
        "description": "使用SentencePiece进行翻译（无需网络）",
        "requires_internet": False,
        "supports_offline": True,
        "quality": "高",
        "speed": "快"
    }
} 
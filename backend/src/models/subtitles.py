"""
AVD Web版本 - 字幕数据库模型

定义字幕任务相关的SQLAlchemy模型
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum
import datetime

from .downloads import Base

class SubtitleStatus(Enum):
    """字幕任务状态枚举"""
    PENDING = "pending"           # 等待处理
    PROCESSING = "processing"     # 处理中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"       # 已取消

class SubtitleTask(Base):
    """字幕任务模型"""
    __tablename__ = "subtitle_tasks"
    __table_args__ = {'extend_existing': True}
    
    # 基础字段
    id = Column(String(36), primary_key=True, index=True)
    
    # 任务类型和状态
    task_type = Column(String(20), default="generate")  # generate, translate, burn
    status = Column(SQLEnum(SubtitleStatus), default=SubtitleStatus.PENDING, index=True)
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    
    # 输入文件信息
    video_file_path = Column(String(500), nullable=True)      # 视频文件路径
    video_url = Column(String(1000), nullable=True)           # 视频URL
    video_title = Column(String(500), nullable=True)          # 视频标题（用于生成有意义的文件名）
    subtitle_file_path = Column(String(500), nullable=True)   # 字幕文件路径
    
    # 生成参数
    language = Column(String(10), default="auto")             # 音频语言
    ai_model_size = Column(String(20), default="base")        # AI模型大小 (重命名避免pydantic冲突)
    translate_to = Column(String(10), nullable=True)          # 翻译目标语言
    download_video = Column(Boolean, default=True)            # 是否下载视频
    
    # 翻译参数
    source_language = Column(String(10), nullable=True)       # 源语言
    target_language = Column(String(10), nullable=True)       # 目标语言
    
    # 字幕烧录参数
    burn_style_options = Column(Text, nullable=True)          # 字幕样式选项 (JSON格式)
    output_video_quality = Column(String(10), default="medium") # 输出视频质量
    preserve_original = Column(Boolean, default=True)         # 是否保留原始视频
    
    # 输出信息
    output_file_path = Column(String(500), nullable=True)     # 输出文件路径
    detected_language = Column(String(10), nullable=True)     # 检测到的语言
    segments_count = Column(Integer, nullable=True)           # 字幕片段数量
    original_file_size = Column(Integer, nullable=True)       # 原始文件大小
    output_file_size = Column(Integer, nullable=True)         # 输出文件大小
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<SubtitleTask(id='{self.id}', status='{self.status.value}', progress={self.progress})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "error_message": self.error_message,
            "video_file_path": self.video_file_path,
            "video_url": self.video_url,
            "video_title": self.video_title,
            "subtitle_file_path": self.subtitle_file_path,
            "language": self.language,
            "model_size": self.ai_model_size,  # 前端仍使用model_size
            "translate_to": self.translate_to,
            "download_video": self.download_video,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "burn_style_options": self.burn_style_options,
            "output_video_quality": self.output_video_quality,
            "preserve_original": self.preserve_original,
            "output_file_path": self.output_file_path,
            "detected_language": self.detected_language,
            "segments_count": self.segments_count,
            "original_file_size": self.original_file_size,
            "output_file_size": self.output_file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        } 
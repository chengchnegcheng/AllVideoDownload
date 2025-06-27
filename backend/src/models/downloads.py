"""
AVD Web版本 - 下载任务数据模型

定义下载任务相关的数据库模型
"""

from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from datetime import datetime
from typing import Optional

Base = declarative_base()

class DownloadStatus(PyEnum):
    """下载状态枚举"""
    PENDING = "pending"        # 等待中
    PROCESSING = "processing"  # 处理中
    DOWNLOADING = "downloading" # 下载中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"    # 已取消
    PAUSED = "paused"         # 已暂停

class DownloadTask(Base):
    """下载任务模型"""
    __tablename__ = "download_tasks"
    
    # 基本信息
    id = Column(String(36), primary_key=True, index=True)  # UUID
    url = Column(Text, nullable=False)  # 原始URL
    title = Column(String(500), nullable=True)  # 视频标题
    description = Column(Text, nullable=True)  # 视频描述
    thumbnail = Column(Text, nullable=True)  # 缩略图URL
    uploader = Column(String(200), nullable=True)  # 上传者
    platform = Column(String(50), nullable=True)  # 平台名称
    
    # 下载配置
    quality = Column(String(20), nullable=False, default="best")  # 画质
    format = Column(String(20), nullable=False, default="mp4")   # 格式
    audio_only = Column(Boolean, default=False)  # 仅音频
    subtitle = Column(Boolean, default=False)    # 下载字幕
    subtitle_language = Column(String(10), default="auto")  # 字幕语言
    output_filename = Column(String(500), nullable=True)  # 自定义文件名
    
    # 状态信息
    status = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING, index=True)
    progress = Column(Float, default=0.0)  # 进度百分比 (0-100)
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # 文件信息
    file_path = Column(Text, nullable=True)  # 本地文件路径
    file_size = Column(Integer, default=0)   # 文件总大小 (字节)
    downloaded_size = Column(Integer, default=0)  # 已下载大小 (字节)
    
    # 性能指标
    download_speed = Column(Float, default=0.0)  # 下载速度 (字节/秒)
    eta = Column(Integer, default=0)  # 预计剩余时间 (秒)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)  # 开始下载时间
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 完成时间
    
    def __repr__(self):
        return f"<DownloadTask(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """计算下载耗时（秒）"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
    
    @property
    def average_speed(self) -> Optional[float]:
        """计算平均下载速度（字节/秒）"""
        duration = self.duration_seconds
        if duration and duration > 0 and self.downloaded_size > 0:
            return self.downloaded_size / duration
        return None
    
    @property
    def progress_percent(self) -> str:
        """格式化的进度百分比"""
        return f"{self.progress:.1f}%"
    
    @property
    def file_size_mb(self) -> Optional[float]:
        """文件大小（MB）"""
        if self.file_size > 0:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    @property
    def downloaded_size_mb(self) -> Optional[float]:
        """已下载大小（MB）"""
        if self.downloaded_size > 0:
            return round(self.downloaded_size / (1024 * 1024), 2)
        return None

# SubtitleTask 模型已移动到 subtitles.py

class UserSession(Base):
    """用户会话模型（用于Cookie管理）"""
    __tablename__ = "user_sessions"
    
    id = Column(String(36), primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # 平台名称
    session_data = Column(Text, nullable=False)  # 加密的Cookie数据
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间
    is_active = Column(Boolean, default=True)  # 是否活跃
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, platform={self.platform})>"

class SystemSettings(Base):
    """系统设置模型"""
    __tablename__ = "system_settings"
    
    key = Column(String(100), primary_key=True, index=True)  # 设置键
    value = Column(Text, nullable=False)  # 设置值
    description = Column(String(500), nullable=True)  # 描述
    category = Column(String(50), default="general")  # 分类
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemSettings(key={self.key}, value={self.value})>" 
"""
AVD Web版本 - 数据库管理模块

提供数据库连接、会话管理和初始化功能
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import OperationalError, DisconnectionError
import logging
import time
from contextlib import contextmanager
from typing import Generator

from .config import settings
from ..models.downloads import Base, SystemSettings
from ..models import subtitles  # 确保导入字幕模型

logger = logging.getLogger(__name__)

# 数据库引擎配置
engine_kwargs = {
    "echo": settings.DEBUG,  # 在调试模式下打印SQL语句
}

# SQLite特殊配置
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "poolclass": StaticPool,
        "connect_args": {
            "check_same_thread": False,  # 允许多线程访问
            "timeout": 20,  # 连接超时
        }
    })

# 创建数据库引擎
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def init_db():
    """初始化数据库
    
    创建所有表并插入默认数据
    """
    try:
        logger.info("正在初始化数据库...")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        # 插入默认设置
        await insert_default_settings()
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

async def insert_default_settings():
    """插入默认系统设置"""
    try:
        with SessionLocal() as db:
            # 检查是否已有设置
            existing_settings = db.query(SystemSettings).first()
            if existing_settings:
                return
            
            # 默认设置列表
            default_settings = [
                {
                    "key": "max_concurrent_downloads",
                    "value": "3",
                    "description": "最大并发下载数",
                    "category": "download"
                },
                {
                    "key": "default_quality",
                    "value": "best",
                    "description": "默认下载质量",
                    "category": "download"
                },
                {
                    "key": "default_format",
                    "value": "mp4",
                    "description": "默认视频格式",
                    "category": "download"
                },
                {
                    "key": "whisper_model_size",
                    "value": "base",
                    "description": "默认AI模型大小",
                    "category": "subtitle"
                },
                {
                    "key": "auto_generate_subtitles",
                    "value": "false",
                    "description": "自动生成字幕",
                    "category": "subtitle"
                },
                {
                    "key": "subtitle_language",
                    "value": "auto",
                    "description": "默认字幕语言",
                    "category": "subtitle"
                },
                {
                    "key": "enable_proxy",
                    "value": "false",
                    "description": "启用代理",
                    "category": "network"
                },
                {
                    "key": "proxy_url",
                    "value": "",
                    "description": "代理服务器地址",
                    "category": "network"
                },
                {
                    "key": "download_timeout",
                    "value": "300",
                    "description": "下载超时时间（秒）",
                    "category": "network"
                },
                {
                    "key": "cleanup_files_after_days",
                    "value": "30",
                    "description": "文件清理间隔（天）",
                    "category": "maintenance"
                }
            ]
            
            # 批量插入设置
            for setting_data in default_settings:
                setting = SystemSettings(**setting_data)
                db.add(setting)
            
            db.commit()
            logger.info(f"已插入 {len(default_settings)} 个默认设置")
            
    except Exception as e:
        logger.error(f"插入默认设置失败: {e}")
        raise

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话
    
    使用依赖注入模式，自动管理会话的生命周期
    
    Yields:
        Session: 数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # 跳过HTTPException，因为这是正常的API错误响应
        from fastapi import HTTPException
        if not isinstance(e, HTTPException):
            error_msg = str(e) if str(e) else f"数据库异常: {type(e).__name__}"
            logger.error(f"数据库会话错误: {error_msg}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_context():
    """获取数据库会话上下文管理器
    
    用于手动管理数据库会话的情况
    
    Returns:
        Session: 数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        # 跳过HTTPException，因为这是正常的API错误响应
        from fastapi import HTTPException
        if not isinstance(e, HTTPException):
            error_msg = str(e) if str(e) else f"数据库异常: {type(e).__name__}"
            logger.error(f"数据库操作错误: {error_msg}")
        db.rollback()
        raise
    finally:
        db.close()

async def cleanup_old_tasks(days: int = 30):
    """清理旧的任务记录
    
    Args:
        days: 保留天数，超过此天数的已完成任务将被删除
    """
    try:
        from datetime import datetime, timedelta
        from ..models.downloads import DownloadTask, DownloadStatus
        from ..models.subtitles import SubtitleTask, SubtitleStatus
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with get_db_context() as db:
            # 删除旧的已完成/失败的下载任务
            deleted_downloads = db.query(DownloadTask).filter(
                DownloadTask.created_at < cutoff_date,
                DownloadTask.status.in_([
                    DownloadStatus.COMPLETED, 
                    DownloadStatus.FAILED, 
                    DownloadStatus.CANCELLED
                ])
            ).delete()
            
            # 删除旧的字幕任务
            deleted_subtitles = db.query(SubtitleTask).filter(
                SubtitleTask.created_at < cutoff_date,
                SubtitleTask.status.in_([
                    SubtitleStatus.COMPLETED, 
                    SubtitleStatus.FAILED, 
                    SubtitleStatus.CANCELLED
                ])
            ).delete()
            
            logger.info(f"清理完成: 删除了 {deleted_downloads} 个下载任务和 {deleted_subtitles} 个字幕任务")
            
    except Exception as e:
        logger.error(f"清理旧任务失败: {e}")
        raise

async def get_setting(key: str, default: str = None) -> str:
    """获取系统设置值
    
    Args:
        key: 设置键名
        default: 默认值
        
    Returns:
        设置值或默认值
    """
    try:
        with get_db_context() as db:
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if setting:
                return setting.value
            return default
    except Exception as e:
        logger.error(f"获取设置失败: {e}")
        return default

async def update_setting(key: str, value: str, description: str = None, category: str = "general"):
    """更新系统设置
    
    Args:
        key: 设置键名
        value: 设置值
        description: 设置描述
        category: 设置分类
    """
    try:
        with get_db_context() as db:
            setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            
            if setting:
                # 更新现有设置
                setting.value = value
                if description:
                    setting.description = description
                setting.category = category
            else:
                # 创建新设置
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description,
                    category=category
                )
                db.add(setting)
            
            logger.info(f"设置已更新: {key} = {value}")
            
    except Exception as e:
        logger.error(f"更新设置失败: {e}")
        raise

async def get_database_stats():
    """获取数据库统计信息
    
    Returns:
        数据库统计信息字典
    """
    try:
        from ..models.downloads import DownloadTask, UserSession, DownloadStatus
        from ..models.subtitles import SubtitleTask
        
        with get_db_context() as db:
            stats = {
                "total_downloads": db.query(DownloadTask).count(),
                "completed_downloads": db.query(DownloadTask).filter(
                    DownloadTask.status == DownloadStatus.COMPLETED
                ).count(),
                "failed_downloads": db.query(DownloadTask).filter(
                    DownloadTask.status == DownloadStatus.FAILED
                ).count(),
                "pending_downloads": db.query(DownloadTask).filter(
                    DownloadTask.status.in_([
                        DownloadStatus.PENDING, 
                        DownloadStatus.PROCESSING,
                        DownloadStatus.DOWNLOADING
                    ])
                ).count(),
                "total_subtitles": db.query(SubtitleTask).count(),
                "active_sessions": db.query(UserSession).filter(
                    UserSession.is_active == True
                ).count(),
                "total_settings": db.query(SystemSettings).count()
            }
            
            return stats
            
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        return {}

def get_db_with_retry(max_retries: int = 3, retry_delay: float = 1.0) -> Generator[Session, None, None]:
    """获取数据库会话（带重试机制）
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        
    Yields:
        Session: 数据库会话对象
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            db = SessionLocal()
            try:
                # 测试连接
                db.execute("SELECT 1")
                yield db
                return
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
                
        except (OperationalError, DisconnectionError) as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                time.sleep(retry_delay)
                continue
            else:
                logger.error(f"数据库连接重试失败: {e}")
                break
        except Exception as e:
            error_msg = str(e) if str(e) else f"数据库异常: {type(e).__name__}"
            logger.error(f"数据库会话错误: {error_msg}")
            raise
    
    # 如果所有重试都失败，抛出最后一个异常
    if last_exception:
        raise last_exception

# 字幕记录管理函数
async def get_subtitle_records(db: Session, page: int = 1, size: int = 10, status: str = None):
    """获取字幕记录列表
    
    Args:
        db: 数据库会话
        page: 页码
        size: 每页大小
        status: 状态筛选
        
    Returns:
        记录列表和总数
    """
    try:
        from ..models.subtitles import SubtitleTask, SubtitleStatus
        
        query = db.query(SubtitleTask).order_by(SubtitleTask.created_at.desc())
        
        # 状态筛选
        if status and status != 'all':
            if status == 'recorded':
                # 'recorded' 映射到 'completed'
                query = query.filter(SubtitleTask.status == SubtitleStatus.COMPLETED)
            elif status == 'completed':
                query = query.filter(SubtitleTask.status == SubtitleStatus.COMPLETED)
            else:
                # 其他状态直接过滤
                try:
                    status_enum = SubtitleStatus(status)
                    query = query.filter(SubtitleTask.status == status_enum)
                except ValueError:
                    pass  # 忽略无效状态
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * size
        records = query.offset(offset).limit(size).all()
        
        # 转换为字典格式
        records_data = []
        for record in records:
            record_dict = record.to_dict()
            # 将status转换为前端期望的格式
            if record_dict['status'] == 'completed':
                record_dict['status'] = 'recorded'  # 前端期望的状态
            records_data.append(record_dict)
        
        return records_data, total
        
    except Exception as e:
        logger.error(f"获取字幕记录失败: {e}")
        raise

async def delete_subtitle_record(db: Session, record_id: str):
    """删除字幕记录
    
    Args:
        db: 数据库会话
        record_id: 记录ID
        
    Returns:
        是否删除成功
    """
    try:
        from ..models.subtitles import SubtitleTask
        
        record = db.query(SubtitleTask).filter(SubtitleTask.id == record_id).first()
        if not record:
            return False
        
        db.delete(record)
        db.commit()
        
        logger.info(f"已删除字幕记录: {record_id}")
        return True
        
    except Exception as e:
        logger.error(f"删除字幕记录失败: {e}")
        db.rollback()
        raise

async def delete_subtitle_records_batch(db: Session, record_ids: list):
    """批量删除字幕记录
    
    Args:
        db: 数据库会话
        record_ids: 记录ID列表
        
    Returns:
        删除的记录数量
    """
    try:
        from ..models.subtitles import SubtitleTask
        
        deleted_count = db.query(SubtitleTask).filter(
            SubtitleTask.id.in_(record_ids)
        ).delete(synchronize_session=False)
        
        db.commit()
        
        logger.info(f"批量删除了 {deleted_count} 个字幕记录")
        return deleted_count
        
    except Exception as e:
        logger.error(f"批量删除字幕记录失败: {e}")
        db.rollback()
        raise

async def create_subtitle_processing_record(
    db: Session,
    record_id: str,
    task_type: str,
    video_url: str = None,
    video_file_path: str = None,
    subtitle_file_path: str = None,
    language: str = "auto",
    model_size: str = "base",
    translate_to: str = None,
    source_language: str = None,
    target_language: str = None
):
    """创建字幕处理记录
    
    Args:
        db: 数据库会话
        record_id: 记录ID
        task_type: 任务类型
        video_url: 视频URL
        video_file_path: 视频文件路径
        subtitle_file_path: 字幕文件路径
        language: 语言
        model_size: 模型大小
        translate_to: 翻译目标语言
        source_language: 源语言
        target_language: 目标语言
        
    Returns:
        创建的记录
    """
    try:
        from ..models.subtitles import SubtitleTask, SubtitleStatus
        
        record = SubtitleTask(
            id=record_id,
            task_type=task_type,
            status=SubtitleStatus.COMPLETED,  # 设置为已完成状态
            video_url=video_url,
            video_file_path=video_file_path,
            subtitle_file_path=subtitle_file_path,
            language=language,
            ai_model_size=model_size,
            translate_to=translate_to,
            source_language=source_language,
            target_language=target_language
        )
        
        db.add(record)
        db.commit()
        db.refresh(record)
        
        logger.info(f"创建字幕处理记录: {record_id}")
        return record
        
    except Exception as e:
        logger.error(f"创建字幕处理记录失败: {e}")
        db.rollback()
        raise

# 数据库健康检查
async def check_database_health():
    """检查数据库连接健康状态
    
    Returns:
        bool: 数据库是否健康
    """
    try:
        with get_db_context() as db:
            # 执行简单查询测试连接
            db.execute("SELECT 1")
            return True
    except Exception as e:
        error_msg = str(e) if str(e) else f"数据库异常: {type(e).__name__}"
        logger.error(f"数据库健康检查失败: {error_msg}")
        return False 
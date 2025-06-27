"""
AVD Web版本 - 下载API路由

提供视频下载相关的RESTful API接口
注意：已移除常规文件下载功能，只保留下载记录和流式下载
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel, HttpUrl
import uuid
import os
import tempfile
from pathlib import Path
from datetime import datetime
import re
import urllib.parse
import asyncio
import logging
import time
from dataclasses import replace

logger = logging.getLogger(__name__)

from ...core.downloader import VideoDownloader
from ...core.downloaders.base_downloader import DownloadOptions
from ...core.database import get_db
from ...models.downloads import DownloadTask, DownloadStatus
from ...core.websocket_manager import websocket_manager
from ...utils.validators import validate_url
from ...core.config import settings, QUALITY_OPTIONS, SUPPORTED_PLATFORMS

router = APIRouter()

# Pydantic模型
class DownloadRequest(BaseModel):
    """下载请求模型"""
    url: HttpUrl
    quality: str = "best"
    format: str = "mp4"
    audio_only: bool = False
    subtitle: bool = False
    subtitle_language: str = "auto"
    output_filename: Optional[str] = None

class VideoInfoResponse(BaseModel):
    """视频信息响应模型"""
    title: str
    description: Optional[str]
    duration: Optional[int]
    thumbnail: Optional[str]
    uploader: Optional[str]
    platform: str
    available_qualities: List[str]
    available_formats: List[str]

class DownloadRecordResponse(BaseModel):
    """下载记录响应模型"""
    record_id: str
    status: str
    message: str

class DownloadListResponse(BaseModel):
    """下载列表响应模型"""
    records: List[dict]
    total: int
    page: int
    size: int

class StreamDownloadRequest(BaseModel):
    """流式下载请求模型"""
    url: HttpUrl
    quality: str = "best"
    format: str = "mp4"
    audio_only: bool = False
    task_id: Optional[str] = None

@router.get("/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    return {
        "platforms": SUPPORTED_PLATFORMS,
        "total": len(SUPPORTED_PLATFORMS)
    }

@router.get("/quality-options")
async def get_quality_options():
    """获取可用的质量选项"""
    return {
        "qualities": QUALITY_OPTIONS,
        "default": "best"
    }

@router.post("/info", response_model=VideoInfoResponse)
async def get_video_info(request: DownloadRequest):
    """获取视频信息
    
    Args:
        request: 包含视频URL的请求
        
    Returns:
        视频的详细信息
        
    Raises:
        HTTPException: 当URL无效或获取信息失败时
    """
    try:
        # 验证URL
        if not validate_url(str(request.url)):
            raise HTTPException(status_code=400, detail="无效的视频URL")
        
        # 创建下载器实例
        downloader = VideoDownloader()
        
        # 获取视频信息
        video_info = await downloader.get_video_info(str(request.url))
        
        if not video_info:
            raise HTTPException(status_code=404, detail="无法获取视频信息，请检查URL是否正确")
        
        return VideoInfoResponse(
            title=video_info.get("title", "未知标题"),
            description=video_info.get("description"),
            duration=int(video_info.get("duration", 0)) if video_info.get("duration") else None,
            thumbnail=video_info.get("thumbnail"),
            uploader=video_info.get("uploader"),
            platform=video_info.get("platform", "unknown"),
            available_qualities=video_info.get("available_qualities", []),
            available_formats=video_info.get("available_formats", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频信息失败: {str(e)}")

@router.post("/record", response_model=DownloadRecordResponse)
async def create_download_record(
    request: DownloadRequest,
    db = Depends(get_db)
):
    """创建下载记录（不实际下载文件到服务器）
    
    Args:
        request: 下载请求参数
        db: 数据库会话
        
    Returns:
        下载记录信息
    """
    try:
        # 验证URL
        if not validate_url(str(request.url)):
            raise HTTPException(status_code=400, detail="无效的视频URL")
        
        # 验证质量选项
        if request.quality not in QUALITY_OPTIONS:
            raise HTTPException(status_code=400, detail="无效的质量选项")
        
        # 获取视频信息用于记录
        downloader = VideoDownloader()
        video_info = await downloader.get_video_info(str(request.url))
        
        # 生成记录ID
        record_id = str(uuid.uuid4())
        
        # 创建下载记录（不实际下载文件）
        record = DownloadTask(
            id=record_id,
            url=str(request.url),
            title=video_info.get("title", "未知标题") if video_info else "未知标题",
            description=video_info.get("description") if video_info else None,
            thumbnail=video_info.get("thumbnail") if video_info else None,
            uploader=video_info.get("uploader") if video_info else None,
            platform=video_info.get("platform", "unknown") if video_info else "unknown",
            quality=request.quality,
            format=request.format,
            audio_only=request.audio_only,
            subtitle=request.subtitle,
            subtitle_language=request.subtitle_language,
            output_filename=request.output_filename,
            status=DownloadStatus.COMPLETED,  # 直接标记为完成，因为只是记录
            progress=100.0,  # 记录创建即为100%
            file_path=None,  # 不存储文件路径
            completed_at=datetime.utcnow()
        )
        
        # 保存到数据库
        db.add(record)
        db.commit()
        
        logger.info(f"创建下载记录成功: {record_id}")
        
        return DownloadRecordResponse(
            record_id=record_id,
            status="recorded",
            message="下载记录已创建，可以使用流式下载获取文件"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建下载记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建下载记录失败: {str(e)}")

@router.get("/records", response_model=DownloadListResponse)
async def get_download_records(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    platform: Optional[str] = Query(None, description="按平台筛选"),
    db = Depends(get_db)
):
    """获取下载记录列表
    
    Args:
        page: 页码
        size: 每页大小
        platform: 平台筛选
        db: 数据库会话
        
    Returns:
        分页的下载记录列表
    """
    try:
        # 构建查询
        query = db.query(DownloadTask)
        
        if platform:
            query = query.filter(DownloadTask.platform == platform)
        
        # 按创建时间倒序排列
        query = query.order_by(DownloadTask.created_at.desc())
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        records = query.offset((page - 1) * size).limit(size).all()
        
        # 转换为字典
        record_list = []
        for record in records:
            record_dict = {
                "id": record.id,
                "url": record.url,
                "title": record.title,
                "description": record.description,
                "thumbnail": record.thumbnail,
                "uploader": record.uploader,
                "platform": record.platform,
                "quality": record.quality,
                "format": record.format,
                "audio_only": record.audio_only,
                "subtitle": record.subtitle,
                "status": record.status.value,
                "created_at": record.created_at.isoformat(),
                "completed_at": record.completed_at.isoformat() if record.completed_at else None
            }
            record_list.append(record_dict)
        
        return DownloadListResponse(
            records=record_list,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记录列表失败: {str(e)}")

@router.get("/records/{record_id}")
async def get_download_record(record_id: str, db = Depends(get_db)):
    """获取特定下载记录的详细信息
    
    Args:
        record_id: 记录ID
        db: 数据库会话
        
    Returns:
        下载记录详细信息
    """
    try:
        record = db.query(DownloadTask).filter(DownloadTask.id == record_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail="下载记录不存在")
        
        return {
            "id": record.id,
            "url": record.url,
            "title": record.title,
            "description": record.description,
            "thumbnail": record.thumbnail,
            "uploader": record.uploader,
            "platform": record.platform,
            "quality": record.quality,
            "format": record.format,
            "audio_only": record.audio_only,
            "subtitle": record.subtitle,
            "subtitle_language": record.subtitle_language,
            "status": record.status.value,
            "created_at": record.created_at.isoformat(),
            "completed_at": record.completed_at.isoformat() if record.completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记录信息失败: {str(e)}")

@router.delete("/records/{record_id}")
async def delete_record(record_id: str, db = Depends(get_db)):
    """删除下载记录
    
    Args:
        record_id: 记录ID
        db: 数据库会话
        
    Returns:
        删除结果
    """
    try:
        record = db.query(DownloadTask).filter(DownloadTask.id == record_id).first()
        
        if not record:
            raise HTTPException(status_code=404, detail="下载记录不存在")
        
        # 从数据库中删除记录
        db.delete(record)
        db.commit()
        
        logger.info(f"删除记录成功: {record_id}")
        
        return {
            "success": True,
            "message": "记录删除成功",
            "record_id": record_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除记录失败: {record_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"删除记录失败: {str(e)}")

@router.delete("/records/batch")
async def delete_records_batch(record_ids: List[str], db = Depends(get_db)):
    """批量删除下载记录
    
    Args:
        record_ids: 记录ID列表
        db: 数据库会话
        
    Returns:
        批量删除结果
    """
    try:
        deleted_count = 0
        failed_count = 0
        
        for record_id in record_ids:
            try:
                record = db.query(DownloadTask).filter(DownloadTask.id == record_id).first()
                
                if not record:
                    failed_count += 1
                    continue
                
                # 从数据库中删除记录
                db.delete(record)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"删除单个记录失败: {record_id}, 错误: {e}")
                failed_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"批量删除完成",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_count": len(record_ids)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"批量删除记录失败, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")

@router.post("/stream")
async def stream_download_video(request: StreamDownloadRequest):
    """流式下载视频（服务器先下载到临时存储，再传输给客户端）
    
    Args:
        request: 流式下载请求
        
    Returns:
        流式下载响应
    """
    temp_file_path = None
    try:
        # 验证URL
        if not validate_url(str(request.url)):
            raise HTTPException(status_code=400, detail="无效的视频URL")
        
        # 验证质量选项
        if request.quality not in QUALITY_OPTIONS:
            raise HTTPException(status_code=400, detail="无效的质量选项")
        
        logger.info(f"开始服务器端下载: {request.url}")
        
        # 创建下载器和选项
        downloader = VideoDownloader()
        options = DownloadOptions(
            quality=request.quality,
            format=request.format,
            audio_only=request.audio_only,
            subtitle=False,
            subtitle_language="auto",
            output_filename=None,
            output_path=tempfile.gettempdir()  # 使用临时目录
        )
        
        # 获取视频信息
        video_info = await downloader.get_video_info(str(request.url))
        if not video_info:
            raise HTTPException(status_code=404, detail="无法获取视频信息")
        
        title = video_info.get("title", "download")
        
        # 生成安全的文件名（保留中文和更多有用字符）
        def sanitize_filename(filename):
            # 移除文件系统不支持的字符，但保留中文、数字、字母、空格、连字符、下划线、括号等
            safe_chars = re.sub(r'[<>:"/\\|?*]', '', filename)  # 只移除文件系统禁用字符
            # 将多个空格或特殊空白字符替换为单个空格
            safe_chars = re.sub(r'\s+', ' ', safe_chars)
            # 移除首尾空格
            safe_chars = safe_chars.strip()
            # 如果文件名为空，使用默认名称
            if not safe_chars:
                return "download"
            # 限制长度（考虑中文字符，使用字节长度限制）
            if len(safe_chars.encode('utf-8')) > 200:  # 限制为200字节，约100个中文字符
                # 逐个字符添加，直到达到字节限制
                result = ""
                for char in safe_chars:
                    test_result = result + char
                    if len(test_result.encode('utf-8')) > 200:
                        break
                    result = test_result
                safe_chars = result.strip()
                if not safe_chars:
                    return "download"
            return safe_chars
        
        safe_title = sanitize_filename(title)
        
        # 创建临时文件
        temp_file_suffix = f".{request.format}"
        temp_fd, temp_file_path = tempfile.mkstemp(suffix=temp_file_suffix, prefix=f"{safe_title}_")
        os.close(temp_fd)  # 关闭文件描述符，我们只需要路径
        
        logger.info(f"开始下载到临时文件: {temp_file_path}")
        
        # 创建WebSocket进度回调函数
        task_id = request.task_id
        async def websocket_progress_callback(progress_data: dict):
            """通过WebSocket发送进度更新"""
            if task_id:
                try:
                    logger.debug(f"WebSocket进度回调被调用 - 任务ID: {task_id}, 进度: {progress_data.get('progress', 0):.1f}%")
                    # 直接发送格式化好的进度数据
                    await websocket_manager.send_download_progress(task_id, progress_data)
                    logger.debug(f"发送进度更新: {task_id} - {progress_data.get('progress', 0)}%")
                    
                except Exception as e:
                    logger.error(f"发送WebSocket进度更新失败: {e}")
        
        # 下载到服务器临时文件（带进度回调）
        download_result = await downloader.download(
            str(request.url), 
            replace(options, output_path=os.path.dirname(temp_file_path)),
            progress_callback=websocket_progress_callback if task_id else None,
            task_id=task_id
        )
        
        if not download_result.get("success"):
            # 发送下载失败的WebSocket消息
            if task_id:
                try:
                    await websocket_manager.send_download_failed(task_id, {
                        "error": download_result.get('error', '未知错误'),
                        "timestamp": time.time()
                    })
                except Exception as e:
                    logger.error(f"发送下载失败消息失败: {e}")
            
            raise HTTPException(
                status_code=500, 
                detail=f"服务器下载失败: {download_result.get('error', '未知错误')}"
            )
        
        # 获取实际下载的文件路径
        actual_file_path = download_result.get("file_path")
        if not actual_file_path or not os.path.exists(actual_file_path):
            # 发送下载失败的WebSocket消息
            if task_id:
                try:
                    await websocket_manager.send_download_failed(task_id, {
                        "error": "下载的文件不存在",
                        "timestamp": time.time()
                    })
                except Exception as e:
                    logger.error(f"发送下载失败消息失败: {e}")
            
            raise HTTPException(status_code=500, detail="下载的文件不存在")
        
        # 更新临时文件路径为实际路径
        temp_file_path = actual_file_path
        
        # 发送下载完成的WebSocket消息
        if task_id:
            try:
                await websocket_manager.send_download_completed(task_id, {
                    "filename": safe_title + "." + request.format,
                    "file_size": os.path.getsize(temp_file_path),
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"发送下载完成消息失败: {e}")
        
        logger.info(f"服务器下载完成，开始传输给客户端: {temp_file_path}")
        
        # 获取文件信息
        file_size = os.path.getsize(temp_file_path)
        filename = f"{safe_title}.{request.format}"
        
        # 创建文件流传输生成器
        async def file_stream_generator():
            try:
                chunk_size = 8192 * 8  # 64KB chunks for better performance
                with open(temp_file_path, 'rb') as file:
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
                logger.info(f"文件传输完成: {filename}")
            except Exception as e:
                logger.error(f"文件传输过程中出错: {e}")
                raise
            finally:
                # 传输完成后清理临时文件
                try:
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        logger.info(f"临时文件已清理: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.error(f"清理临时文件失败: {cleanup_error}")
        
        # 设置响应头（支持中文文件名）
        def encode_filename_for_download(filename):
            """编码文件名以支持各种浏览器和中文字符"""
            # 对于现代浏览器，使用 UTF-8 编码的文件名
            try:
                # 使用 RFC 6266 标准的编码方式
                encoded_filename = urllib.parse.quote(filename.encode('utf-8'))
                return f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
            except Exception:
                # 如果编码失败，回退到简单的ASCII文件名
                ascii_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
                return f'attachment; filename="{ascii_filename}"'
        
        response_headers = {
            "Content-Disposition": encode_filename_for_download(filename),
            "Content-Type": f"video/{request.format}" if not request.audio_only else f"audio/{request.format}",
            "Content-Length": str(file_size),
            "Cache-Control": "no-cache",
            "Accept-Ranges": "bytes"
        }
        
        return StreamingResponse(
            file_stream_generator(),
            media_type=f"video/{request.format}" if not request.audio_only else f"audio/{request.format}",
            headers=response_headers
        )
        
    except HTTPException:
        # 如果是HTTP异常，清理临时文件后重新抛出
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"异常时清理临时文件: {temp_file_path}")
            except:
                pass
        raise
    except Exception as e:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"异常时清理临时文件: {temp_file_path}")
            except:
                pass
        
        logger.error(f"流式下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

# 移除了以下已弃用的端点：
# - /start (常规下载)
# - /tasks (下载任务管理)
# - /tasks/{task_id} (任务详情)
# - /tasks/{task_id}/download (文件下载)
# - /tasks/{task_id}/cancel (任务取消)
# - /tasks/{task_id}/progress (任务进度)
# - /tasks/active/progress (活跃任务进度)

# 这些功能已被简化的记录系统和流式下载取代 
"""
字幕新版本主模块 - 整合所有拆分的字幕功能
"""

from fastapi import APIRouter, HTTPException, File, UploadFile
from pathlib import Path
import uuid
import os
import json
from datetime import datetime
import logging

from ....core.config import settings
from .subtitle_info import router as info_router
from .subtitle_files import router as files_router
from .subtitle_tasks import router as tasks_router
from .subtitle_processor import router as processor_router
from .subtitle_settings import router as settings_router

logger = logging.getLogger(__name__)
router = APIRouter()

# 包含所有子模块的路由
router.include_router(info_router, prefix="/info", tags=["字幕信息"])
router.include_router(files_router, prefix="/files", tags=["字幕文件"])
router.include_router(tasks_router, prefix="/tasks", tags=["字幕任务"])
router.include_router(processor_router, prefix="/processor", tags=["字幕处理"])
router.include_router(settings_router, prefix="/settings", tags=["字幕设置"])

@router.get("/")
async def subtitle_root():
    """字幕系统根路径"""
    return {
        "message": "字幕系统新版本",
        "version": "2.0",
        "modules": [
            "info - 字幕信息", 
            "files - 字幕文件",
            "tasks - 字幕任务",
            "processor - 字幕处理",
            "settings - 字幕设置"
        ]
    }

@router.post("/upload")
async def upload_subtitle_file(file: UploadFile = File(...)):
    """上传字幕文件"""
    try:
        logger.info(f"开始上传文件: {file.filename}, 类型: {file.content_type}")
        
        # 检查文件是否存在
        if not file or not file.filename:
            logger.error("没有接收到文件或文件名为空")
            raise HTTPException(status_code=400, detail="没有选择文件")
        
        # 检查文件类型
        subtitle_extensions = {'.srt', '.vtt', '.ass', '.ssa', '.sub'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}
        allowed_extensions = subtitle_extensions | video_extensions
        
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = os.path.join(settings.FILES_PATH, filename)
        
        # 确保文件目录存在
        os.makedirs(settings.FILES_PATH, exist_ok=True)
        
        # 保存文件
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # 创建文件名映射文件
        original_filename = file.filename
        original_title = Path(original_filename).stem  # 去掉扩展名作为标题
        
        # 在同一目录下保存映射信息
        mapping_file = os.path.join(settings.FILES_PATH, f"{file_id}_mapping.json")
        mapping_info = {
            "original_filename": original_filename,
            "original_title": original_title,
            "uuid_filename": filename,
            "file_path": file_path,
            "upload_time": datetime.utcnow().isoformat(),
            "file_size": len(content)
        }
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"文件保存成功: {file_path}")
        logger.info(f"映射信息保存成功: {mapping_file}")
        
        file_type = "视频文件" if file_ext in video_extensions else "字幕文件"
        
        return {
            "message": f"{file_type}上传成功",
            "file_path": file_path,
            "filename": filename,
            "original_filename": original_filename,
            "original_title": original_title,
            "file_id": file_id,
            "file_type": file_type,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}") 
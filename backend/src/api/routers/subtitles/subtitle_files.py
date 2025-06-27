"""
字幕文件操作API

包含文件上传、下载等文件操作功能
"""

from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
import uuid
import os
import tempfile
import json
from pathlib import Path
import logging

from ....core.config import settings
from .subtitle_utils import encode_filename_for_download

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_subtitle_file(file: UploadFile = File(...)):
    """上传字幕文件或视频文件"""
    try:
        # 验证文件类型
        allowed_extensions = {
            # 字幕文件
            '.srt', '.vtt', '.ass', '.ssa', '.sub', '.idx', '.sup',
            # 视频文件  
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp',
            # 音频文件
            '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.wma', '.flac'
        }
        
        file_ext = Path(file.filename or '').suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_ext}. 支持的类型: {', '.join(allowed_extensions)}"
            )
        
        # 检查文件大小 (最大1GB)
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大支持 {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}{file_ext}"
        file_path = Path(settings.FILES_PATH) / safe_filename
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # 保存文件映射信息
        mapping_info = {
            'original_filename': file.filename,
            'upload_time': str(Path(file_path).stat().st_mtime),
            'file_size': len(file_content),
            'file_type': file_ext,
            'content_type': file.content_type
        }
        
        mapping_file = file_path.parent / f"{file_id}_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"开始上传文件: {file.filename}, 类型: {file.content_type}")
        logger.info(f"文件保存成功: {file_path}")
        logger.info(f"映射信息保存成功: {mapping_file}")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "file_id": file_id,
            "file_path": str(file_path),
            "original_filename": file.filename,
            "file_size": len(file_content),
            "file_type": file_ext
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.get("/download/{record_id}")
async def download_processed_file(record_id: str):
    """下载处理完成的字幕文件"""
    try:
        # 在临时文件目录中查找相关的字幕文件
        temp_files_dir = Path(settings.FILES_PATH)
        
        # 优先查找翻译后的字幕文件（带_zh_subtitles或_subtitles后缀）
        possible_patterns = [
            f"{record_id}_zh_subtitles.srt",  # 翻译后的中文字幕
            f"{record_id}_subtitles.srt",     # 原始字幕
            f"{record_id}.srt"                # 简单格式
        ]
        
        target_file = None
        for pattern in possible_patterns:
            file_path = temp_files_dir / pattern
            if file_path.exists():
                target_file = file_path
                break
        
        # 如果没有找到特定文件，查找最新的字幕文件
        if not target_file:
            srt_files = list(temp_files_dir.glob("*.srt"))
            if srt_files:
                target_file = max(srt_files, key=lambda f: f.stat().st_mtime)
        
        if not target_file or not target_file.exists():
            raise HTTPException(status_code=404, detail="文件不存在或已被清理")
        
        temp_file_path = str(target_file)
        
        # 生成更友好的文件名
        filename = target_file.name
        
        # 尝试从映射文件获取原始文件名
        mapping_file = temp_files_dir / f"{record_id}_mapping.json"
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_info = json.load(f)
                    original_name = mapping_info.get('original_filename', filename)
                    if original_name:
                        # 构造更友好的下载文件名
                        base_name = Path(original_name).stem
                        if '_zh_subtitles' in filename:
                            filename = f"{base_name}_中文字幕.srt"
                        elif '_subtitles' in filename:
                            filename = f"{base_name}_字幕.srt"
                        else:
                            filename = f"{base_name}.srt"
            except Exception as e:
                logger.warning(f"读取映射文件失败: {e}")
        
        file_size = os.path.getsize(temp_file_path)
        
        # 创建文件流（不自动删除文件，保留一段时间供重复下载）
        async def file_generator():
            try:
                chunk_size = 8192
                total_bytes_sent = 0
                with open(temp_file_path, 'rb') as file:
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
                        total_bytes_sent += len(chunk)
                
                logger.info(f"文件下载完成: {filename} (共传输 {total_bytes_sent} 字节)")
                
            except Exception as e:
                logger.error(f"文件下载出错: {str(e)}")
                raise
        
        # 返回文件响应
        response_headers = {
            "Content-Disposition": encode_filename_for_download(filename),
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Length": str(file_size),
            "Cache-Control": "no-cache"
        }
        
        return StreamingResponse(
            file_generator(),
            media_type="application/octet-stream",
            headers=response_headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}") 
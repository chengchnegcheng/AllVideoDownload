"""
字幕处理API v2 - 高品质版本

实现用户要求的三个核心功能：
1. 从URL生成字幕
2. 从文件生成字幕  
3. 翻译字幕文件

统一使用最高品质设置，自动清理临时文件
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import json
import asyncio
import logging
from pathlib import Path

from ...core.config import settings
from ...core.database import get_db
from ...core.subtitle_processor_v2 import get_subtitle_processor_v2_instance
from ...utils.validators import validate_url

logger = logging.getLogger(__name__)
router = APIRouter()

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh': '中文',
    'zh-cn': '简体中文', 
    'zh-tw': '繁体中文',
    'en': '英语',
    'ja': '日语',
    'ko': '韩语',
    'fr': '法语',
    'de': '德语',
    'es': '西班牙语',
    'ru': '俄语',
    'ar': '阿拉伯语',
    'hi': '印地语',
    'pt': '葡萄牙语',
    'it': '意大利语',
    'th': '泰语',
    'vi': '越南语'
}

@router.post("/v2/generate-from-url")
async def generate_subtitles_from_url_v2(request: dict, db: Session = Depends(get_db)):
    """
    从URL生成字幕（最高品质）
    
    流程：下载视频到files文件夹 -> 音频提取 -> faster-whisper最高品质 -> 高品质翻译 -> 浏览器下载 -> 自动清理
    """
    try:
        video_url = request.get('video_url')
        target_language = request.get('target_language', 'zh')
        
        if not video_url:
            raise HTTPException(status_code=400, detail="缺少video_url参数")
        
        if not validate_url(video_url):
            raise HTTPException(status_code=400, detail="无效的视频URL")
        
        if target_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail=f"不支持的目标语言: {target_language}")
        
        logger.info(f"开始从URL生成字幕: {video_url}")
        
        # 获取字幕处理器实例
        processor = get_subtitle_processor_v2_instance()
        
        # 处理字幕生成
        result = await processor.process_from_url(
            video_url=video_url,
            target_language=target_language
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', '处理失败'))
        
        # 准备下载文件
        subtitle_file = result.get('subtitle_file')
        download_filename = result.get('download_filename')
        temp_files = result.get('temp_files', [])
        
        if not os.path.exists(subtitle_file):
            raise HTTPException(status_code=404, detail="生成的字幕文件不存在")
        
        # 返回文件流
        async def file_stream_generator():
            try:
                with open(subtitle_file, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            finally:
                # 文件传输完成后清理临时文件
                await processor._cleanup_temp_files(temp_files)
        
        return StreamingResponse(
            file_stream_generator(),
            media_type='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{download_filename}"',
                'Cache-Control': 'no-cache'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从URL生成字幕失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成字幕失败: {str(e)}")

@router.post("/v2/generate-from-file")
async def generate_subtitles_from_file_v2(
    file: UploadFile = File(...),
    target_language: str = Form('zh'),
    db: Session = Depends(get_db)
):
    """
    从文件生成字幕（最高品质）
    
    流程：上传到files文件夹 -> 音频提取 -> faster-whisper最高品质 -> 高品质翻译 -> 浏览器下载 -> 自动清理
    """
    temp_files = []
    
    try:
        if target_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail=f"不支持的目标语言: {target_language}")
        
        # 验证文件类型
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp3', '.wav', '.m4a', '.flac']
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")
        
        logger.info(f"开始从文件生成字幕: {file.filename}")
        
        # 保存上传的文件到files文件夹
        upload_id = str(uuid.uuid4())
        temp_video_path = Path(settings.FILES_PATH) / f"{upload_id}{file_ext}"
        temp_files.append(str(temp_video_path))
        
        # 写入文件
        with open(temp_video_path, 'wb') as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 获取字幕处理器实例
        processor = get_subtitle_processor_v2_instance()
        
        # 处理字幕生成
        result = await processor.process_from_file(
            video_file_path=str(temp_video_path),
            target_language=target_language
        )
        
        if not result.get('success'):
            # 清理上传的文件
            await processor._cleanup_temp_files(temp_files)
            raise HTTPException(status_code=500, detail=result.get('error', '处理失败'))
        
        # 准备下载文件
        subtitle_file = result.get('subtitle_file')
        download_filename = result.get('download_filename')
        result_temp_files = result.get('temp_files', [])
        
        # 合并临时文件列表
        all_temp_files = temp_files + result_temp_files
        
        if not os.path.exists(subtitle_file):
            await processor._cleanup_temp_files(all_temp_files)
            raise HTTPException(status_code=404, detail="生成的字幕文件不存在")
        
        # 返回文件流
        async def file_stream_generator():
            try:
                with open(subtitle_file, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            finally:
                # 文件传输完成后清理所有临时文件
                await processor._cleanup_temp_files(all_temp_files)
        
        return StreamingResponse(
            file_stream_generator(),
            media_type='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{download_filename}"',
                'Cache-Control': 'no-cache'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从文件生成字幕失败: {e}")
        # 清理临时文件
        processor = get_subtitle_processor_v2_instance()
        await processor._cleanup_temp_files(temp_files)
        raise HTTPException(status_code=500, detail=f"生成字幕失败: {str(e)}")

@router.post("/v2/translate-subtitle")
async def translate_subtitle_v2(
    file: UploadFile = File(...),
    target_language: str = Form('zh'),
    db: Session = Depends(get_db)
):
    """
    翻译字幕文件（最高品质）
    
    流程：上传到files文件夹 -> 高品质翻译 -> 浏览器下载 -> 自动清理
    """
    temp_files = []
    
    try:
        if target_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail=f"不支持的目标语言: {target_language}")
        
        # 验证字幕文件类型
        allowed_extensions = ['.srt', '.vtt', '.ass', '.ssa']
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的字幕文件类型: {file_ext}")
        
        logger.info(f"开始翻译字幕文件: {file.filename}")
        
        # 保存上传的字幕文件到files文件夹
        upload_id = str(uuid.uuid4())
        temp_subtitle_path = Path(settings.FILES_PATH) / f"{upload_id}{file_ext}"
        temp_files.append(str(temp_subtitle_path))
        
        # 写入文件
        with open(temp_subtitle_path, 'wb') as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 获取字幕处理器实例
        processor = get_subtitle_processor_v2_instance()
        
        # 处理字幕翻译
        result = await processor.translate_subtitle_file(
            subtitle_file_path=str(temp_subtitle_path),
            target_language=target_language
        )
        
        if not result.get('success'):
            # 清理上传的文件
            await processor._cleanup_temp_files(temp_files)
            raise HTTPException(status_code=500, detail=result.get('error', '翻译失败'))
        
        # 准备下载文件
        subtitle_file = result.get('subtitle_file')
        download_filename = result.get('download_filename')
        result_temp_files = result.get('temp_files', [])
        
        # 合并临时文件列表
        all_temp_files = temp_files + result_temp_files
        
        if not os.path.exists(subtitle_file):
            await processor._cleanup_temp_files(all_temp_files)
            raise HTTPException(status_code=404, detail="翻译的字幕文件不存在")
        
        # 返回文件流
        async def file_stream_generator():
            try:
                with open(subtitle_file, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            finally:
                # 文件传输完成后清理所有临时文件
                await processor._cleanup_temp_files(all_temp_files)
        
        return StreamingResponse(
            file_stream_generator(),
            media_type='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{download_filename}"',
                'Cache-Control': 'no-cache'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"翻译字幕文件失败: {e}")
        # 清理临时文件
        processor = get_subtitle_processor_v2_instance()
        await processor._cleanup_temp_files(temp_files)
        raise HTTPException(status_code=500, detail=f"翻译字幕失败: {str(e)}")

@router.post("/v2/stream-generate-from-url")
async def stream_generate_from_url_v2(request: dict):
    """
    从URL生成字幕（流式响应，显示进度）
    """
    async def progress_stream():
        try:
            video_url = request.get('video_url')
            target_language = request.get('target_language', 'zh')
            
            if not video_url:
                yield f"data: {json.dumps({'error': '缺少video_url参数', 'status': 'error'})}\n\n"
                return
                
            if not validate_url(video_url):
                yield f"data: {json.dumps({'error': '无效的视频URL', 'status': 'error'})}\n\n"
                return
            
            if target_language not in SUPPORTED_LANGUAGES:
                yield f"data: {json.dumps({'error': f'不支持的目标语言: {target_language}', 'status': 'error'})}\n\n"
                return
            
            # 发送初始状态
            yield f"data: {json.dumps({'progress': 0, 'message': '正在初始化...', 'status': 'processing'})}\n\n"
            
            processor = get_subtitle_processor_v2_instance()
            
            # 创建进度回调
            async def progress_callback(progress: float, message: str = ""):
                yield f"data: {json.dumps({'progress': progress, 'message': message, 'status': 'processing'})}\n\n"
            
            # 启动处理任务
            result = await processor.process_from_url(
                video_url=video_url,
                target_language=target_language,
                progress_callback=progress_callback
            )
            
            if result.get('success'):
                subtitle_file = result.get('subtitle_file')
                download_filename = result.get('download_filename')
                
                data = {
                    'progress': 100, 
                    'message': '处理完成！', 
                    'status': 'completed',
                    'download_filename': download_filename,
                    'subtitle_file': subtitle_file,
                    'title': result.get('title'),
                    'duration': result.get('duration')
                }
                yield f"data: {json.dumps(data)}\n\n"
            else:
                yield f"data: {json.dumps({'error': result.get('error', '未知错误'), 'status': 'error'})}\n\n"
                
        except Exception as e:
            logger.error(f"流式生成字幕失败: {e}")
            yield f"data: {json.dumps({'error': f'处理失败: {str(e)}', 'status': 'error'})}\n\n"
    
    return StreamingResponse(
        progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.post("/v2/stream-generate-from-file")
async def stream_generate_from_file_v2(
    file: UploadFile = File(...),
    target_language: str = Form('zh')
):
    """
    从文件生成字幕（流式响应，显示进度）
    """
    async def progress_stream():
        temp_files = []
        try:
            if target_language not in SUPPORTED_LANGUAGES:
                yield f"data: {json.dumps({'error': f'不支持的目标语言: {target_language}', 'status': 'error'})}\n\n"
                return
            
            # 验证文件类型
            allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mp3', '.wav', '.m4a', '.flac']
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                yield f"data: {json.dumps({'error': f'不支持的文件类型: {file_ext}', 'status': 'error'})}\n\n"
                return
            
            # 发送初始状态
            yield f"data: {json.dumps({'progress': 0, 'message': '正在上传文件...', 'status': 'processing'})}\n\n"
            
            # 保存上传的文件
            upload_id = str(uuid.uuid4())
            temp_video_path = Path(settings.FILES_PATH) / f"{upload_id}{file_ext}"
            temp_files.append(str(temp_video_path))
            
            with open(temp_video_path, 'wb') as buffer:
                content = await file.read()
                buffer.write(content)
            
            yield f"data: {json.dumps({'progress': 5, 'message': '文件上传完成，开始处理...', 'status': 'processing'})}\n\n"
            
            processor = get_subtitle_processor_v2_instance()
            
            # 创建进度回调
            async def progress_callback(progress: float, message: str = ""):
                mapped_progress = 5 + (progress * 0.95)  # 映射到5-100%
                yield f"data: {json.dumps({'progress': mapped_progress, 'message': message, 'status': 'processing'})}\n\n"
            
            # 启动处理任务
            result = await processor.process_from_file(
                video_file_path=str(temp_video_path),
                target_language=target_language,
                progress_callback=progress_callback
            )
            
            if result.get('success'):
                subtitle_file = result.get('subtitle_file')
                download_filename = result.get('download_filename')
                result_temp_files = result.get('temp_files', [])
                temp_files.extend(result_temp_files)
                
                data = {
                    'progress': 100, 
                    'message': '处理完成！', 
                    'status': 'completed',
                    'download_filename': download_filename,
                    'subtitle_file': subtitle_file,
                    'title': result.get('title'),
                    'duration': result.get('duration')
                }
                yield f"data: {json.dumps(data)}\n\n"
            else:
                yield f"data: {json.dumps({'error': result.get('error', '未知错误'), 'status': 'error'})}\n\n"
                
        except Exception as e:
            logger.error(f"流式生成字幕失败: {e}")
            yield f"data: {json.dumps({'error': f'处理失败: {str(e)}', 'status': 'error'})}\n\n"
        finally:
            # 清理临时文件
            if temp_files:
                processor = get_subtitle_processor_v2_instance()
                await processor._cleanup_temp_files(temp_files)
    
    return StreamingResponse(
        progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.post("/v2/stream-translate-subtitle")
async def stream_translate_subtitle_v2(
    file: UploadFile = File(...),
    target_language: str = Form('zh')
):
    """
    翻译字幕文件（流式响应，显示进度）
    """
    async def progress_stream():
        temp_files = []
        try:
            if target_language not in SUPPORTED_LANGUAGES:
                yield f"data: {json.dumps({'error': f'不支持的目标语言: {target_language}', 'status': 'error'})}\n\n"
                return
            
            # 验证字幕文件类型
            allowed_extensions = ['.srt', '.vtt', '.ass', '.ssa']
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                yield f"data: {json.dumps({'error': f'不支持的字幕文件类型: {file_ext}', 'status': 'error'})}\n\n"
                return
            
            # 发送初始状态
            yield f"data: {json.dumps({'progress': 0, 'message': '正在上传字幕文件...', 'status': 'processing'})}\n\n"
            
            # 保存上传的字幕文件
            upload_id = str(uuid.uuid4())
            temp_subtitle_path = Path(settings.FILES_PATH) / f"{upload_id}{file_ext}"
            temp_files.append(str(temp_subtitle_path))
            
            with open(temp_subtitle_path, 'wb') as buffer:
                content = await file.read()
                buffer.write(content)
            
            yield f"data: {json.dumps({'progress': 5, 'message': '文件上传完成，开始翻译...', 'status': 'processing'})}\n\n"
            
            processor = get_subtitle_processor_v2_instance()
            
            # 创建进度回调
            async def progress_callback(progress: float, message: str = ""):
                mapped_progress = 5 + (progress * 0.95)  # 映射到5-100%
                yield f"data: {json.dumps({'progress': mapped_progress, 'message': message, 'status': 'processing'})}\n\n"
            
            # 启动翻译任务
            result = await processor.translate_subtitle_file(
                subtitle_file_path=str(temp_subtitle_path),
                target_language=target_language,
                progress_callback=progress_callback
            )
            
            if result.get('success'):
                subtitle_file = result.get('subtitle_file')
                download_filename = result.get('download_filename')
                result_temp_files = result.get('temp_files', [])
                temp_files.extend(result_temp_files)
                
                data = {
                    'progress': 100, 
                    'message': '翻译完成！', 
                    'status': 'completed',
                    'download_filename': download_filename,
                    'subtitle_file': subtitle_file,
                    'title': result.get('title'),
                    'stats': result.get('stats')
                }
                yield f"data: {json.dumps(data)}\n\n"
            else:
                yield f"data: {json.dumps({'error': result.get('error', '未知错误'), 'status': 'error'})}\n\n"
                
        except Exception as e:
            logger.error(f"流式翻译字幕失败: {e}")
            yield f"data: {json.dumps({'error': f'翻译失败: {str(e)}', 'status': 'error'})}\n\n"
        finally:
            # 清理临时文件
            if temp_files:
                processor = get_subtitle_processor_v2_instance()
                await processor._cleanup_temp_files(temp_files)
    
    return StreamingResponse(
        progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.get("/v2/download/{file_id}")
async def download_subtitle_file_v2(file_id: str):
    """
    下载生成的字幕文件
    """
    try:
        file_path = Path(settings.FILES_PATH) / f"{file_id}.srt"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            path=str(file_path),
            media_type='text/plain; charset=utf-8',
            filename=f"subtitle_{file_id}.srt",
            headers={'Cache-Control': 'no-cache'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载字幕文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@router.get("/v2/supported-languages")
async def get_supported_languages_v2():
    """
    获取支持的语言列表
    """
    return {
        'success': True,
        'languages': SUPPORTED_LANGUAGES
    }
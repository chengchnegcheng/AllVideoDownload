"""
字幕核心处理模块 - 处理字幕生成、烧录等核心功能
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
import os
import json
import asyncio
import threading
import time
import logging
from pathlib import Path

from ....core.config import settings
from ....core.database import get_db, create_subtitle_processing_record
from ....core.subtitle_processor import get_subtitle_processor_instance
from ....core.downloader import VideoDownloader
from ....utils.validators import validate_url

logger = logging.getLogger(__name__)
router = APIRouter()

# 全局任务管理器
class TaskManager:
    def __init__(self):
        self.active_tasks = {}  # task_id -> {"status": "running|cancelled|completed", "thread": thread_obj}
        self.lock = threading.Lock()
    
    def start_task(self, task_id: str, thread_obj=None):
        with self.lock:
            self.active_tasks[task_id] = {
                "status": "running",
                "thread": thread_obj,
                "start_time": time.time()
            }
    
    def cancel_task(self, task_id: str):
        with self.lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "cancelled"
                return True
            return False
    
    def complete_task(self, task_id: str):
        with self.lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["status"] = "completed"
    
    def is_cancelled(self, task_id: str):
        with self.lock:
            return self.active_tasks.get(task_id, {}).get("status") == "cancelled"
    
    def cleanup_task(self, task_id: str):
        with self.lock:
            self.active_tasks.pop(task_id, None)
    
    def get_active_tasks(self):
        with self.lock:
            return list(self.active_tasks.keys())

# 全局任务管理器实例
task_manager = TaskManager()

# 支持的字幕语言映射
SUBTITLE_LANGUAGES = {
    'zh': '中文', 'en': '英语', 'ja': '日语', 'ko': '韩语', 
    'fr': '法语', 'de': '德语', 'es': '西班牙语', 'it': '意大利语',
    'pt': '葡萄牙语', 'ru': '俄语', 'ar': '阿拉伯语', 'hi': '印地语'
}

def get_original_title_from_path(file_path: str) -> str:
    """从文件路径获取原始标题，优先使用映射文件信息"""
    try:
        if not file_path or not os.path.exists(file_path):
            return "untitled"
        
        # 获取文件目录和基本名称
        file_dir = os.path.dirname(file_path)
        file_stem = Path(file_path).stem
        
        # 检查是否是UUID格式的文件名
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        uuid_match = re.match(uuid_pattern, file_stem, re.IGNORECASE)
        
        if uuid_match:
            # 如果是UUID文件名，尝试从映射文件获取原始标题
            uuid_part = uuid_match.group(0)
            mapping_file = os.path.join(file_dir, f"{uuid_part}_mapping.json")
            
            if os.path.exists(mapping_file):
                try:
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_info = json.load(f)
                        original_title = mapping_info.get('original_title')
                        if original_title:
                            return original_title
                except Exception as e:
                    logger.warning(f"读取映射文件失败: {e}")
            
            # 如果映射文件不存在，使用默认标题
            return "video"
        else:
            # 如果不是UUID格式，直接使用文件名作为标题
            return file_stem
            
    except Exception as e:
        logger.error(f"获取原始标题失败: {e}")
        return "untitled"

@router.post("/stream")
async def stream_subtitle_processing(request: dict, db: Session = Depends(get_db)):
    """流式字幕处理 - 重写版本，使用SSE实时推送进度"""
    
    # 验证基本参数
    operation = request.get('operation')
    if not operation:
        raise HTTPException(status_code=400, detail="缺少operation参数")
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 进度状态管理
    progress_state = {
        'current_progress': 0,
        'current_message': '初始化...',
        'is_completed': False,
        'has_error': False,
        'error_message': '',
        'result_data': None
    }

    async def execute_subtitle_task():
        """执行字幕处理任务的核心逻辑"""
        try:
            processor = get_subtitle_processor_instance()
            
            # 更新进度的辅助函数
            async def update_progress(progress: float, message: str = ""):
                progress_state['current_progress'] = min(max(float(progress), 0), 100)
                progress_state['current_message'] = message
                
            await update_progress(5, "开始处理...")
            
            if operation == 'generate':
                # 字幕生成
                video_url = request.get('video_url')
                video_file_path = request.get('video_file_path')
                language = request.get('language', 'auto')
                model_size = request.get('model_size', 'large-v3')
                target_language = request.get('target_language')
                quality_mode = request.get('quality_mode', 'balance')
                
                if video_url:
                    # 从URL生成
                    await update_progress(10, "从URL生成字幕...")
                    result = await processor.process_from_url(
                        video_url=video_url,
                        source_language=language,
                        model_size=model_size,
                        target_language=target_language,
                        quality_mode=quality_mode,
                        task_id=task_id
                    )
                elif video_file_path:
                    # 从文件生成
                    await update_progress(10, "从文件生成字幕...")
                    
                    # 构建完整路径
                    if not os.path.isabs(video_file_path):
                        video_file_path = os.path.join(settings.FILES_PATH, video_file_path)
                    
                    result = await processor.process_from_file(
                        video_file_path=video_file_path,
                        source_language=language,
                        model_size=model_size,
                        target_language=target_language,
                        quality_mode=quality_mode,
                        task_id=task_id
                    )
                else:
                    raise ValueError("缺少video_url或video_file_path参数")
                    
            elif operation == 'translate':
                # 字幕翻译
                subtitle_file_path = request.get('subtitle_file_path')
                source_language = request.get('source_language', 'auto')
                target_language = request.get('target_language')
                translation_method = request.get('translation_method', 'optimized')
                quality_mode = request.get('quality_mode', 'balance')
                
                if not subtitle_file_path:
                    raise ValueError("缺少subtitle_file_path参数")
                if not target_language:
                    raise ValueError("缺少target_language参数")
                
                # 构建完整路径
                if not os.path.isabs(subtitle_file_path):
                    subtitle_file_path = os.path.join(settings.FILES_PATH, subtitle_file_path)
                
                await update_progress(10, "翻译字幕...")
                result = await processor.translate_subtitle_file(
                    subtitle_path=subtitle_file_path,
                    source_language=source_language,
                    target_language=target_language,
                    translation_method=translation_method,
                    quality_mode=quality_mode,
                    task_id=task_id
                )
            else:
                raise ValueError(f"不支持的操作类型: {operation}")
            
            # 检查处理结果
            if result.get('success'):
                await update_progress(100, "处理完成!")
                progress_state['result_data'] = result
                progress_state['is_completed'] = True
            else:
                progress_state['has_error'] = True
                progress_state['error_message'] = result.get('error', '处理失败')
                
        except Exception as e:
            logger.error(f"字幕处理任务失败: {e}")
            progress_state['has_error'] = True
            progress_state['error_message'] = str(e)

    async def progress_stream():
        """生成SSE进度流"""
        try:
            # 发送初始状态
            yield f"data: {json.dumps({'progress': 0, 'message': '初始化...', 'status': 'processing'})}\n\n"
            
            # 启动处理任务
            task = asyncio.create_task(execute_subtitle_task())
            
            # 监控进度并发送更新
            last_progress = -1
            last_message = ""
            
            while not progress_state['is_completed'] and not progress_state['has_error']:
                current_progress = progress_state['current_progress']
                current_message = progress_state['current_message']
                
                # 只有进度或消息发生变化时才发送更新
                if current_progress != last_progress or current_message != last_message:
                    yield f"data: {json.dumps({'progress': current_progress, 'message': current_message, 'status': 'processing'})}\n\n"
                    last_progress = current_progress
                    last_message = current_message
                
                await asyncio.sleep(0.5)  # 每0.5秒检查一次
            
            # 等待任务完成
            await task
            
            # 发送最终结果
            if progress_state['has_error']:
                yield f"data: {json.dumps({'error': progress_state['error_message'], 'status': 'error'})}\n\n"
            else:
                result_data = progress_state['result_data']
                if result_data and result_data.get('success'):
                    # 准备下载信息
                    subtitle_file = result_data.get('subtitle_file') or result_data.get('translated_file')
                    if subtitle_file:
                        # 生成下载文件名
                        title = result_data.get('title', 'subtitle')
                        target_lang = result_data.get('target_language', '')
                        if target_lang:
                            download_filename = f"{title}_{target_lang}.srt"
                        else:
                            download_filename = f"{title}.srt"
                        
                        # 从文件路径提取记录ID
                        record_id = os.path.basename(subtitle_file).replace('.srt', '')
                        
                        completion_data = {
                            'progress': 100,
                            'message': '处理完成!',
                            'status': 'completed',
                            'download_ready': True,
                            'record_id': record_id,
                            'filename': download_filename,
                            'subtitle_file': subtitle_file,
                            'duration': result_data.get('duration'),
                            'quality_info': result_data.get('quality_info', ''),
                            'model_used': result_data.get('model_used', ''),
                        }
                        
                        yield f"data: {json.dumps(completion_data)}\n\n"
                        yield f"data: [DONE]\n\n"
                    else:
                        yield f"data: {json.dumps({'error': '未找到字幕文件', 'status': 'error'})}\n\n"
                else:
                    yield f"data: {json.dumps({'error': '处理失败', 'status': 'error'})}\n\n"
                    
        except Exception as e:
            logger.error(f"SSE流处理失败: {e}")
            yield f"data: {json.dumps({'error': f'流处理失败: {str(e)}', 'status': 'error'})}\n\n"

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

@router.post("/burn")
async def burn_subtitles_to_video(request: dict):
    """将字幕烧录到视频文件中"""
    try:
        video_file_path = request.get('video_file_path')
        subtitle_file_path = request.get('subtitle_file_path')
        output_filename = request.get('output_filename', 'output_with_subtitles.mp4')
        
        if not video_file_path:
            raise HTTPException(status_code=400, detail="缺少video_file_path参数")
        if not subtitle_file_path:
            raise HTTPException(status_code=400, detail="缺少subtitle_file_path参数")
        
        if not os.path.exists(video_file_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")
        if not os.path.exists(subtitle_file_path):
            raise HTTPException(status_code=404, detail="字幕文件不存在")
        
        # 生成输出文件路径
        output_path = os.path.join(settings.FILES_PATH, output_filename)
        
        # 确保输出文件名唯一
        base_name, ext = os.path.splitext(output_filename)
        counter = 1
        while os.path.exists(output_path):
            new_filename = f"{base_name}_{counter}{ext}"
            output_path = os.path.join(settings.FILES_PATH, new_filename)
            counter += 1
            if counter > 100:  # 防止无限循环
                raise HTTPException(status_code=500, detail="无法生成唯一的输出文件名")
        
        final_filename = os.path.basename(output_path)
        
        # 使用字幕处理器进行烧录
        processor = get_subtitle_processor_instance()
        
        # 执行烧录
        result = await processor.burn_subtitles_to_video(
            video_file_path, 
            subtitle_file_path, 
            output_path
        )
        
        if result.get('success'):
            # 编码文件名用于下载
            def encode_video_filename_for_download(filename):
                """对文件名进行编码以支持中文下载"""
                import urllib.parse
                return urllib.parse.quote(filename.encode('utf-8'))
            
            encoded_filename = encode_video_filename_for_download(final_filename)
            
            # 流式返回视频文件
            async def video_stream_generator():
                try:
                    with open(output_path, 'rb') as video_file:
                        while True:
                            chunk = video_file.read(8192)  # 8KB chunks
                            if not chunk:
                                break
                            yield chunk
                except Exception as e:
                    logger.error(f"视频流读取失败: {e}")
                    raise
            
            return StreamingResponse(
                video_stream_generator(),
                media_type='video/mp4',
                headers={
                    'Content-Disposition': f'attachment; filename*=UTF-8\'\'{encoded_filename}',
                    'Cache-Control': 'no-cache'
                }
            )
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '字幕烧录失败'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"字幕烧录失败: {e}")
        raise HTTPException(status_code=500, detail=f"字幕烧录失败: {str(e)}")

@router.post("/generate-from-url")
async def generate_subtitles_from_url(request: dict, db: Session = Depends(get_db)):
    """从URL生成字幕 - 重写版本"""
    try:
        # 验证必需参数
        video_url = request.get('video_url')
        if not video_url:
            raise HTTPException(status_code=400, detail="缺少video_url参数")
        
        if not validate_url(video_url):
            raise HTTPException(status_code=400, detail="无效的视频URL")
        
        # 获取处理参数
        language = request.get('language', 'auto')
        model_size = request.get('model_size', 'large-v3')  # 默认使用最新模型
        target_language = request.get('target_language')  # 翻译目标语言
        quality_mode = request.get('quality_mode', 'balance')  # quality/balance/speed
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 启动后台任务
        task_manager.start_task(task_id)
        
        try:
            processor = get_subtitle_processor_instance()
            
            # 执行字幕生成
            result = await processor.process_from_url(
                video_url=video_url,
                source_language=language,
                model_size=model_size,
                target_language=target_language,
                quality_mode=quality_mode,
                task_id=task_id
            )
            
            # 检查任务是否被取消
            if task_manager.is_cancelled(task_id):
                task_manager.cleanup_task(task_id)
                raise HTTPException(status_code=499, detail="任务已被取消")
            
            # 标记任务完成
            task_manager.complete_task(task_id)
            
            # 保存处理记录到数据库
            if result.get('success') and result.get('subtitle_file'):
                await create_subtitle_processing_record(
                    db=db,
                    source_type='url',
                    source_path=video_url,
                    result_path=result['subtitle_file'],
                    language=language,
                    model_size=model_size,
                    target_language=target_language,
                    task_id=task_id
                )
            
            return {
                "success": True,
                "task_id": task_id,
                "data": result
            }
            
        except Exception as e:
            task_manager.cleanup_task(task_id)
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从URL生成字幕失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成字幕失败: {str(e)}")

@router.post("/generate-from-file") 
async def generate_subtitles_from_file(request: dict, db: Session = Depends(get_db)):
    """从文件生成字幕 - 重写版本"""
    try:
        # 验证必需参数
        video_file_path = request.get('video_file_path')
        if not video_file_path:
            raise HTTPException(status_code=400, detail="缺少video_file_path参数")
        
        # 构建完整文件路径
        if not os.path.isabs(video_file_path):
            video_file_path = os.path.join(settings.FILES_PATH, video_file_path)
        
        if not os.path.exists(video_file_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        # 获取处理参数
        language = request.get('language', 'auto')
        model_size = request.get('model_size', 'large-v3')  # 默认使用最新模型
        target_language = request.get('target_language')  # 翻译目标语言
        quality_mode = request.get('quality_mode', 'balance')  # quality/balance/speed
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 启动后台任务
        task_manager.start_task(task_id)
        
        try:
            processor = get_subtitle_processor_instance()
            
            # 执行字幕生成
            result = await processor.process_from_file(
                video_file_path=video_file_path,
                source_language=language,
                model_size=model_size,
                target_language=target_language,
                quality_mode=quality_mode,
                task_id=task_id
            )
            
            # 检查任务是否被取消
            if task_manager.is_cancelled(task_id):
                task_manager.cleanup_task(task_id)
                raise HTTPException(status_code=499, detail="任务已被取消")
            
            # 标记任务完成
            task_manager.complete_task(task_id)
            
            # 保存处理记录到数据库
            if result.get('success') and result.get('subtitle_file'):
                await create_subtitle_processing_record(
                    db=db,
                    source_type='file',
                    source_path=video_file_path,
                    result_path=result['subtitle_file'],
                    language=language,
                    model_size=model_size,
                    target_language=target_language,
                    task_id=task_id
                )
            
            return {
                "success": True,
                "task_id": task_id,
                "data": result
            }
            
        except Exception as e:
            task_manager.cleanup_task(task_id)
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从文件生成字幕失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成字幕失败: {str(e)}")

@router.post("/translate-subtitle")
async def translate_subtitle(request: dict, db: Session = Depends(get_db)):
    """翻译字幕文件 - 重写版本"""
    try:
        # 验证必需参数
        subtitle_file_path = request.get('subtitle_file_path')
        target_language = request.get('target_language')
        
        if not subtitle_file_path:
            raise HTTPException(status_code=400, detail="缺少subtitle_file_path参数")
        
        if not target_language:
            raise HTTPException(status_code=400, detail="缺少target_language参数")
        
        # 构建完整文件路径
        if not os.path.isabs(subtitle_file_path):
            subtitle_file_path = os.path.join(settings.FILES_PATH, subtitle_file_path)
        
        if not os.path.exists(subtitle_file_path):
            raise HTTPException(status_code=404, detail="字幕文件不存在")
        
        # 获取处理参数
        source_language = request.get('source_language', 'auto')
        translation_method = request.get('translation_method', 'optimized')  # optimized/enhanced/basic
        quality_mode = request.get('quality_mode', 'balance')  # quality/balance/speed
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 启动后台任务
        task_manager.start_task(task_id)
        
        try:
            processor = get_subtitle_processor_instance()
            
            # 执行字幕翻译
            result = await processor.translate_subtitle_file(
                subtitle_path=subtitle_file_path,
                source_language=source_language,
                target_language=target_language,
                translation_method=translation_method,
                quality_mode=quality_mode,
                task_id=task_id
            )
            
            # 检查任务是否被取消
            if task_manager.is_cancelled(task_id):
                task_manager.cleanup_task(task_id)
                raise HTTPException(status_code=499, detail="任务已被取消")
            
            # 标记任务完成
            task_manager.complete_task(task_id)
            
            # 保存处理记录到数据库
            if result.get('success') and result.get('translated_file'):
                await create_subtitle_processing_record(
                    db=db,
                    source_type='subtitle',
                    source_path=subtitle_file_path,
                    result_path=result['translated_file'],
                    language=source_language,
                    target_language=target_language,
                    task_id=task_id
                )
            
            return {
                "success": True,
                "task_id": task_id,
                "data": result
            }
            
        except Exception as e:
            task_manager.cleanup_task(task_id)
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"翻译字幕失败: {e}")
        raise HTTPException(status_code=500, detail=f"翻译字幕失败: {str(e)}")

@router.get("/config")
async def get_subtitle_config():
    """获取字幕处理配置信息 - 重写版本"""
    try:
        processor = get_subtitle_processor_instance()
        
        return {
            "success": True,
            "data": {
                "supported_languages": processor.get_supported_languages(),
                "supported_models": processor.get_supported_models(),
                "quality_modes": processor.get_quality_modes(),
                "default_model": "large-v3",
                "default_quality_mode": "balance",
                "translation_methods": {
                    "optimized": "优化翻译器 (推荐)",
                    "enhanced": "增强翻译器",
                    "basic": "基础翻译器"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取配置信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.get("/models")
async def get_available_models():
    """获取可用的AI模型列表"""
    try:
        processor = get_subtitle_processor_instance()
        models = processor.get_supported_models()
        
        return {
            "success": True,
            "models": models,
            "recommended": "large-v3"
        }
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型失败: {str(e)}")

@router.get("/languages")
async def get_supported_languages():
    """获取支持的语言列表"""
    try:
        processor = get_subtitle_processor_instance()
        languages = processor.get_supported_languages()
        
        return {
            "success": True,
            "languages": languages,
            "auto_detect": True
        }
        
    except Exception as e:
        logger.error(f"获取语言列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取语言失败: {str(e)}")

@router.post("/validate")
async def validate_subtitle_request(request: dict):
    """验证字幕处理请求参数"""
    try:
        operation = request.get('operation')
        if not operation:
            return {
                "valid": False,
                "error": "缺少operation参数"
            }
        
        if operation == 'generate':
            video_url = request.get('video_url')
            video_file_path = request.get('video_file_path')
            
            if not video_url and not video_file_path:
                return {
                    "valid": False,
                    "error": "生成字幕需要提供video_url或video_file_path"
                }
            
            if video_url and not validate_url(video_url):
                return {
                    "valid": False,
                    "error": "无效的视频URL"
                }
            
            if video_file_path and not os.path.exists(
                os.path.join(settings.FILES_PATH, video_file_path) 
                if not os.path.isabs(video_file_path) else video_file_path
            ):
                return {
                    "valid": False,
                    "error": "视频文件不存在"
                }
                
        elif operation == 'translate':
            subtitle_file_path = request.get('subtitle_file_path')
            target_language = request.get('target_language')
            
            if not subtitle_file_path:
                return {
                    "valid": False,
                    "error": "翻译字幕需要提供subtitle_file_path"
                }
                
            if not target_language:
                return {
                    "valid": False,
                    "error": "翻译字幕需要提供target_language"
                }
            
            # 检查字幕文件是否存在
            full_path = (
                os.path.join(settings.FILES_PATH, subtitle_file_path)
                if not os.path.isabs(subtitle_file_path)
                else subtitle_file_path
            )
            if not os.path.exists(full_path):
                return {
                    "valid": False,
                    "error": "字幕文件不存在"
                }
        else:
            return {
                "valid": False,
                "error": f"不支持的操作类型: {operation}"
            }
        
        return {
            "valid": True,
            "message": "请求参数验证通过"
        }
        
    except Exception as e:
        logger.error(f"验证请求参数失败: {e}")
        return {
            "valid": False,
            "error": f"验证失败: {str(e)}"
        }

@router.post("/cancel-task")
async def cancel_task(request: dict):
    """取消正在进行的任务"""
    try:
        task_id = request.get('task_id')
        
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少task_id参数")
        
        # 首先尝试后台任务管理器
        try:
            from ....core.task_manager import get_task_manager
            task_manager_bg = get_task_manager()
            result = await task_manager_bg.cancel_task(task_id)
            
            if result:
                logger.info(f"后台任务 {task_id} 已取消")
                return {
                    "success": True,
                    "message": f"后台任务 {task_id} 取消成功",
                    "task_id": task_id,
                    "method": "background_manager"
                }
        except Exception as e:
            logger.debug(f"后台任务管理器取消失败: {e}")
        
        # 尝试简单任务管理器
        cancelled = task_manager.cancel_task(task_id)
        
        if cancelled:
            logger.info(f"简单任务 {task_id} 已标记为取消")
            
            # 尝试清理相关资源
            try:
                processor = get_subtitle_processor_instance()
                # 如果处理器有清理方法，调用它
                if hasattr(processor, 'cancel_task'):
                    await processor.cancel_task(task_id)
                logger.info(f"任务 {task_id} 资源清理完成")
            except Exception as e:
                logger.warning(f"清理任务资源失败: {e}")
            
            return {
                "success": True,
                "message": f"任务 {task_id} 取消成功",
                "task_id": task_id,
                "method": "simple_manager"
            }
        else:
            return {
                "success": False,
                "message": f"任务 {task_id} 不存在或已完成",
                "task_id": task_id
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        task_status = task_manager.active_tasks.get(task_id)
        
        if not task_status:
            return {
                "task_id": task_id,
                "status": "not_found",
                "message": "任务不存在"
            }
        
        return {
            "task_id": task_id,
            "status": task_status["status"],
            "start_time": task_status.get("start_time"),
            "running_time": time.time() - task_status.get("start_time", time.time())
        }
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

@router.get("/active-tasks")
async def get_active_tasks():
    """获取所有活跃任务"""
    try:
        active_tasks = task_manager.get_active_tasks()
        
        task_details = []
        for task_id in active_tasks:
            task_info = task_manager.active_tasks.get(task_id, {})
            task_details.append({
                "task_id": task_id,
                "status": task_info.get("status", "unknown"),
                "start_time": task_info.get("start_time"),
                "running_time": time.time() - task_info.get("start_time", time.time())
            })
        
        return {
            "success": True,
            "active_tasks": task_details,
            "total_count": len(task_details)
        }
        
    except Exception as e:
        logger.error(f"获取活跃任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取活跃任务失败: {str(e)}")

@router.post("/test-optimized-translator")
async def test_optimized_translator(request: dict):
    """测试优化版翻译器"""
    try:
        subtitle_file_path = request.get('subtitle_file_path')
        source_language = request.get('source_language', 'auto')
        target_language = request.get('target_language', 'zh')
        
        if not subtitle_file_path:
            raise HTTPException(status_code=400, detail="缺少subtitle_file_path参数")
        
        # 构建完整路径
        full_subtitle_path = os.path.join(str(settings.FILES_PATH), subtitle_file_path)
        
        if not os.path.exists(full_subtitle_path):
            raise HTTPException(status_code=404, detail=f"字幕文件不存在: {subtitle_file_path}")
        
        # 获取处理器实例
        processor = get_subtitle_processor_instance()
        
        # 直接调用翻译方法
        result = await processor.translate_subtitles(
            subtitle_path=full_subtitle_path,
            source_language=source_language,
            target_language=target_language
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试优化版翻译器失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}") 
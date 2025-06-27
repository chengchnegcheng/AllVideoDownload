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
    """流式字幕处理 - 实现服务器推送事件(SSE)"""    
    # 使用共享状态来传递进度
    progress_state = {
        'current_progress': 0,
        'current_message': '初始化...',
        'is_completed': False,
        'has_error': False,
        'error_message': '',
        'result_data': None
    }

    async def progress_stream():
        """生成SSE进度流"""
        try:
            operation = request.get('operation')
            if not operation:
                yield f"data: {json.dumps({'error': '缺少operation参数', 'status': 'error'})}\n\n"
                return
            
            # 发送初始状态
            yield f"data: {json.dumps({'progress': 0, 'message': '正在初始化...', 'status': 'processing'})}\n\n"
            await asyncio.sleep(0.1)
            
            # 启动处理任务
            async def process_subtitle_task_simple(request: dict, state: dict):
                """简化的字幕处理任务（新流程：faster-whisper最高品质+SentencePiece翻译）"""
                try:
                    # 在函数开始就导入os模块以避免作用域问题
                    import os as path_utils
                    processor = get_subtitle_processor_instance()
                    
                    # 创建进度回调函数
                    async def update_progress(progress: float, message: str = ""):
                        state['current_progress'] = min(max(float(progress), 0), 100)
                        state['current_message'] = message
                        logger.info(f"进度更新: {progress:.1f}% - {message}")
                    
                    operation = request.get('operation')
                    if operation == 'translate':
                        # 字幕翻译处理（新流程：SentencePiece最高品质翻译）
                        subtitle_file_path = request.get('subtitle_file_path')
                        source_language = request.get('source_language', 'auto')
                        target_language = request.get('target_language')
                        original_title = request.get('original_title', 'subtitle')
                        prefer_local_filename = request.get('prefer_local_filename', False)
                        
                        if not subtitle_file_path:
                            state['has_error'] = True
                            state['error_message'] = '缺少subtitle_file_path参数'
                            return
                        
                        if not target_language:
                            state['has_error'] = True
                            state['error_message'] = '缺少target_language参数'
                            return
                        
                        # 构建完整的文件路径
                        full_subtitle_path = path_utils.path.join(str(settings.FILES_PATH), subtitle_file_path)
                        
                        if not path_utils.path.exists(full_subtitle_path):
                            state['has_error'] = True
                            state['error_message'] = f'字幕文件不存在: {subtitle_file_path}'
                            return
                        
                        await update_progress(10, "开始优化版翻译器翻译...")
                        
                        # 执行翻译（不使用进度回调以避免作用域问题）
                        result_data = await processor.translate_subtitles(
                            subtitle_path=full_subtitle_path,
                            source_language=source_language,
                            target_language=target_language,
                            progress_callback=None  # 避免异步回调问题
                        )
                        
                        if result_data.get('success'):
                            # 构建翻译后的文件标题
                            target_lang_name = SUBTITLE_LANGUAGES.get(target_language, target_language)
                            if prefer_local_filename and original_title:
                                title = f"{original_title}_{target_lang_name}"
                            else:
                                title = f"translated_{target_lang_name}_subtitle"
                            
                            result_data['title'] = title
                            result_data['quality_info'] = "SentencePiece最高品质翻译"
                            
                            # 关键修复：映射字段用于下载处理
                            if 'translated_file' in result_data and not result_data.get('subtitle_file'):
                                result_data['subtitle_file'] = result_data['translated_file']
                            
                            state['result_data'] = result_data
                            state['is_completed'] = True
                            await update_progress(100, "SentencePiece翻译完成！")
                        else:
                            state['has_error'] = True
                            state['error_message'] = result_data.get('error', '翻译失败')
                            return
                        
                    elif operation == 'generate':
                        video_url = request.get('video_url')
                        video_file_path = request.get('video_file_path')
                        language = request.get('language', 'auto')
                        ai_model_size = "large-v3"  # 强制使用最高品质模型
                        translate_to = request.get('translate_to')
                        
                        original_title = request.get('original_title')
                        prefer_local_filename = request.get('prefer_local_filename', False)
                        
                        title = "subtitle"
                        
                        if video_url:
                            # 从URL生成字幕（新流程：下载+faster-whisper最高品质+SentencePiece翻译+自动清理）
                            if not validate_url(video_url):
                                state['has_error'] = True
                                state['error_message'] = '无效的视频URL'
                                return
                            
                            await update_progress(5, "准备从URL下载到服务器files文件夹...")
                            
                            # 确定标题
                            if original_title and prefer_local_filename:
                                title = original_title
                            elif original_title:
                                title = original_title
                            else:
                                downloader = VideoDownloader()
                                video_info = await downloader.get_video_info(video_url)
                                title = video_info.get("title", "subtitle") if video_info else "subtitle"
                            
                            await update_progress(10, "开始从URL生成字幕（faster-whisper最高品质+SentencePiece翻译）...")
                            
                            # 创建简单的进度回调
                            async def url_progress_callback(progress: float, message: str = ""):
                                mapped_progress = 10 + (progress * 0.85)  # 10-95%
                                await update_progress(mapped_progress, message)
                            
                            # 使用新流程：强制最高品质+自动翻译
                            result_data = await processor.generate_subtitles_from_url(
                                video_url,
                                language=language,
                                model_size=ai_model_size,  # 强制使用large-v3
                                translate_to=translate_to,
                                download_video=False,  # 不保留视频文件
                                progress_callback=url_progress_callback
                            )
                            
                        elif video_file_path:
                            # 从文件生成字幕（新流程：faster-whisper最高品质+SentencePiece翻译+自动清理）
                            if not path_utils.path.exists(video_file_path):
                                state['has_error'] = True
                                state['error_message'] = '视频文件不存在'
                                return
                            
                            # 确定标题
                            if original_title and prefer_local_filename:
                                title = original_title
                            elif original_title:
                                title = original_title
                            else:
                                title = get_original_title_from_path(video_file_path)
                            
                            await update_progress(10, "开始从文件生成字幕（faster-whisper最高品质+SentencePiece翻译）...")
                            
                            # 创建文件进度回调
                            async def file_progress_callback(progress: float, message: str = ""):
                                mapped_progress = 10 + (progress * 0.85)  # 10-95%
                                await update_progress(mapped_progress, message)
                            
                            # 使用新流程：强制最高品质+自动翻译
                            result_data = await processor.generate_subtitles(
                                video_file_path,
                                language=language,
                                model_size=ai_model_size,  # 强制使用large-v3
                                auto_translate=bool(translate_to),
                                target_language=translate_to or "zh",
                                progress_callback=file_progress_callback
                            )
                            
                        else:
                            state['has_error'] = True
                            state['error_message'] = '缺少video_url或video_file_path参数'
                            return
                        
                        # 保存结果
                        if result_data.get('success'):
                            # 构建标题
                            if translate_to:
                                target_lang_name = SUBTITLE_LANGUAGES.get(translate_to, translate_to)
                                title = f"{title}_{target_lang_name}"
                            
                            result_data['title'] = title
                            result_data['quality_info'] = "faster-whisper最高品质+SentencePiece翻译"
                            state['result_data'] = result_data
                            state['is_completed'] = True
                            await update_progress(100, "处理完成！")
                        else:
                            state['has_error'] = True
                            state['error_message'] = result_data.get('error', '生成失败')
                            return
                        
                    else:
                        # 未知操作
                        state['has_error'] = True
                        state['error_message'] = f'不支持的操作类型: {operation}'
                        return
                        
                except Exception as e:
                    logger.error(f"处理任务失败: {e}")
                    state['has_error'] = True
                    state['error_message'] = str(e)
            
            # 启动后台任务
            task = asyncio.create_task(process_subtitle_task_simple(request, progress_state))
            
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
            try:
                await task
            except Exception as e:
                logger.error(f"任务执行异常: {e}")
                progress_state['has_error'] = True
                progress_state['error_message'] = str(e)
            
            # 发送最终结果
            if progress_state['has_error']:
                yield f"data: {json.dumps({'error': progress_state['error_message'], 'status': 'error'})}\n\n"
            else:
                # 清理文件名用于下载
                def sanitize_filename(filename):
                    invalid_chars = '<>:"/\\|?*'
                    for char in invalid_chars:
                        filename = filename.replace(char, '_')
                    return filename
                
                result_data = progress_state['result_data']
                if result_data and result_data.get('success'):
                    download_filename = sanitize_filename(f"{result_data.get('title', 'subtitle')}.srt")
                    
                    # 从字幕文件路径提取记录ID用于下载，支持多种字段名
                    subtitle_file_path = result_data.get('subtitle_file') or result_data.get('translated_file', '')
                    record_id = ""
                    if subtitle_file_path:
                        # 提取文件名中的UUID部分  
                        import os
                        file_name = os.path.basename(subtitle_file_path)
                        # 支持格式: uuid.srt, uuid_zh_subtitles.srt, uuid_subtitles.srt, uuid_zh_en_subtitles.srt
                        if '_zh_en_subtitles.srt' in file_name:
                            record_id = file_name.replace('_zh_en_subtitles.srt', '')
                        elif '_zh_subtitles.srt' in file_name:
                            record_id = file_name.replace('_zh_subtitles.srt', '')
                        elif '_subtitles.srt' in file_name:
                            record_id = file_name.replace('_subtitles.srt', '')
                        elif file_name.endswith('.srt'):
                            record_id = file_name.replace('.srt', '')
                    
                    # 构建完成响应数据
                    completion_data = {
                        'progress': 100, 
                        'message': '处理完成！', 
                        'status': 'completed',
                        'download_ready': True,
                        'record_id': record_id,
                        'filename': download_filename,
                        'subtitle_file': subtitle_file_path,  # 直接使用已获取的文件路径
                        'duration': result_data.get('duration')
                    }
                    
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    
                    # 发送结束信号触发前端下载
                    yield f"data: [DONE]\n\n"
                else:
                    yield f"data: {json.dumps({'error': result_data.get('error', '未知错误'), 'status': 'error'})}\n\n"
                    
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
    """从URL生成字幕（非流式版本）"""
    try:
        video_url = request.get('video_url')
        language = request.get('language', 'auto')
        model_size = request.get('model_size', 'base')
        
        if not video_url:
            raise HTTPException(status_code=400, detail="缺少video_url参数")
        
        if not validate_url(video_url):
            raise HTTPException(status_code=400, detail="无效的视频URL")
        
        processor = get_subtitle_processor_instance()
        result = await processor.generate_subtitles_from_url(
            video_url, 
            language=language, 
            model_size=model_size
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从URL生成字幕失败: {e}")
        raise HTTPException(status_code=500, detail=f"从URL生成字幕失败: {str(e)}")

@router.post("/generate-from-file") 
async def generate_subtitles_from_file(request: dict, db: Session = Depends(get_db)):
    """从文件生成字幕（非流式版本）"""
    try:
        video_file_path = request.get('video_file_path')
        language = request.get('language', 'auto')
        model_size = request.get('model_size', 'base')
        
        if not video_file_path:
            raise HTTPException(status_code=400, detail="缺少video_file_path参数")
        
        if not os.path.exists(video_file_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        processor = get_subtitle_processor_instance()
        result = await processor.generate_subtitles(
            video_file_path, 
            language=language, 
            model_size=model_size
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从文件生成字幕失败: {e}")
        raise HTTPException(status_code=500, detail=f"从文件生成字幕失败: {str(e)}")

@router.post("/cancel-task")
async def cancel_task(request: dict):
    """取消正在进行的任务"""
    try:
        task_id = request.get('task_id')
        
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少task_id参数")
        
        # 尝试取消任务
        cancelled = task_manager.cancel_task(task_id)
        
        if cancelled:
            logger.info(f"任务 {task_id} 已标记为取消")
            return {
                "success": True,
                "message": f"任务 {task_id} 取消成功",
                "task_id": task_id
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
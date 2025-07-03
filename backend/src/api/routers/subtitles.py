"""
AVD Web版本 - 字幕处理API - 重写优化版

统一的字幕处理接口，包含：
1. URL生成字幕
2. 文件生成字幕
3. 字幕翻译
4. 进度跟踪和管理

特点：
- 简化的API设计
- 统一的错误处理
- 实时进度反馈
- 自动资源管理
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import os
import json
import uuid
import asyncio
import time
import logging
from pathlib import Path
from datetime import datetime

from ...core.config import settings
from ...core.database import get_db, create_subtitle_processing_record
from ...core.subtitle_processor import get_subtitle_processor_instance
from ...utils.validators import validate_url

logger = logging.getLogger(__name__)
router = APIRouter()

# 全局任务管理
import traceback

class SimpleTaskManager:
    def __init__(self):
        self.tasks = {}  # task_id -> task_info
    
    def create_task(self, task_id: str, operation: str, params: dict) -> dict:
        """创建新任务"""
        task_info = {
            'task_id': task_id,
            'operation': operation,
            'params': params,
            'status': 'pending',
            'progress': 0,
            'message': '准备开始...',
            'start_time': time.time(),
            'error': None,
            'result': None
        }
        self.tasks[task_id] = task_info
        return task_info
    
    async def update_task(self, task_id: str, **updates):
        """更新任务状态并推送到前端"""
        if task_id in self.tasks:
            self.tasks[task_id].update(updates)
            
            # 添加时间戳
            self.tasks[task_id]['timestamp'] = time.time()
            
            # 推送进度到WebSocket
            await self._send_progress_update(task_id, self.tasks[task_id])
    
    async def _send_progress_update(self, task_id: str, task_info: dict):
        """发送进度更新到WebSocket - 增强版本"""
        try:
            from ...core.websocket_manager import websocket_manager
            
            progress_data = {
                'task_id': task_id,
                'status': task_info.get('status'),
                'progress': task_info.get('progress', 0),
                'message': task_info.get('message', ''),
                'operation': task_info.get('operation'),
                'timestamp': task_info.get('timestamp', time.time())
            }
            
            # 如果任务完成，添加结果信息
            if task_info.get('status') == 'completed' and task_info.get('result'):
                progress_data['result'] = task_info['result']
            
            # 如果任务失败，添加错误信息并强制推送
            if task_info.get('status') == 'failed':
                progress_data['error'] = task_info.get('error', '处理失败')
                progress_data['progress'] = 0  # 失败时进度重置为0
                # 立即推送失败状态
                logger.error(f"任务失败，立即推送状态: {task_id} - {progress_data['error']}")
            
            # 推送到WebSocket
            await websocket_manager.send_subtitle_progress(task_id, progress_data)
            
            # 增强日志记录
            if task_info.get('status') == 'failed':
                logger.error(f"❌ 已推送失败状态: {task_id} -> {progress_data['error']}")
            elif task_info.get('status') == 'completed':
                logger.info(f"✅ 已推送完成状态: {task_id} -> {progress_data['progress']}%")
            else:
                logger.debug(f"📊 已推送进度状态: {task_id} -> {progress_data['progress']}% - {progress_data['message']}")
            
        except Exception as e:
            logger.error(f"推送进度更新失败: {e}")
            # 如果WebSocket推送失败，记录详细错误信息
            import traceback
            logger.error(f"推送错误详情: {traceback.format_exc()}")
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否被取消"""
        task = self.tasks.get(task_id)
        return task and task.get('status') == 'cancelled'
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = 'cancelled'
            return True
        return False
    
    def cleanup_task(self, task_id: str):
        """清理任务"""
        self.tasks.pop(task_id, None)

# 全局任务管理器实例
task_manager = SimpleTaskManager()

def get_original_title_from_file_path(file_path: str) -> str:
    """从文件路径获取原始标题"""
    try:
        if not file_path:
            return "untitled"
            
        # 获取文件基本信息
        file_stem = Path(file_path).stem
        file_dir = os.path.dirname(file_path)
        
        # 检查是否是UUID格式的文件名
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        if re.match(uuid_pattern, file_stem, re.IGNORECASE):
            # 是UUID文件名，从映射文件获取原始标题
            mapping_file = os.path.join(file_dir, f"{file_stem}_mapping.json")
            if os.path.exists(mapping_file):
                try:
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_info = json.load(f)
                        original_title = mapping_info.get('original_title')
                        if original_title:
                            logger.info(f"从映射文件获取原始标题: {original_title}")
                            return original_title
                        
                        # 如果没有original_title，使用original_filename去除扩展名
                        original_filename = mapping_info.get('original_filename')
                        if original_filename:
                            original_title = Path(original_filename).stem
                            logger.info(f"从原始文件名提取标题: {original_title}")
                            return original_title
                except Exception as e:
                    logger.warning(f"读取映射文件失败: {e}")
            else:
                logger.warning(f"映射文件不存在: {mapping_file}")
        
        # 如果不是UUID或没有映射文件，直接使用文件名
        return file_stem
        
    except Exception as e:
        logger.error(f"获取原始标题失败: {e}")
        return "untitled"

@router.get("/")
async def subtitle_root():
    """字幕系统根路径"""
    return {
        "message": "字幕处理系统 - 重写优化版",
        "version": "3.0",
        "features": [
            "URL生成字幕",
            "文件生成字幕", 
            "字幕翻译",
            "实时进度跟踪",
            "多格式支持"
        ]
    }

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件 - 优化版
    支持视频文件和字幕文件
    """
    try:
        logger.info(f"开始上传文件: {file.filename}")
        
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="没有选择文件")
        
        # 检查文件类型
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        subtitle_exts = {'.srt', '.vtt', '.ass', '.ssa', '.sub'}
        allowed_exts = video_exts | subtitle_exts
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        # 生成文件ID和路径
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = os.path.join(settings.FILES_PATH, filename)
        
        # 确保目录存在
        os.makedirs(settings.FILES_PATH, exist_ok=True)
        
        # 保存文件
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # 保存文件映射信息
        original_title = Path(file.filename).stem
        mapping_file = os.path.join(settings.FILES_PATH, f"{file_id}_mapping.json")
        mapping_info = {
            "original_filename": file.filename,
            "original_title": original_title,
            "uuid_filename": filename,
            "file_path": file_path,
            "upload_time": datetime.utcnow().isoformat(),
            "file_size": len(content),
            "file_type": "video" if file_ext in video_exts else "subtitle"
        }
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"文件上传成功: {file_path}")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "file_id": file_id,
            "filename": filename,
            "original_filename": file.filename,
            "original_title": original_title,
            "file_path": file_path,
            "file_type": mapping_info["file_type"],
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/process")
async def process_subtitle(request: dict):
    """
    统一字幕处理接口 - 重写优化版
    
    支持操作：
    - generate_from_url: 从URL生成字幕
    - generate_from_file: 从文件生成字幕
    - translate: 翻译字幕
    """
    try:
        operation = request.get('operation')
        if not operation:
            raise HTTPException(status_code=400, detail="缺少operation参数")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        task_info = task_manager.create_task(task_id, operation, request)
        
        # 异步执行处理
        asyncio.create_task(_execute_subtitle_processing(task_id, operation, request))
        
        return {
            "success": True,
            "task_id": task_id,
            "message": f"任务已创建，操作: {operation}",
            "status_url": f"/api/v1/subtitles/status/{task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建字幕处理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

async def _execute_subtitle_processing(task_id: str, operation: str, request: dict):
    """执行字幕处理的后台任务 - 增强错误处理版本"""
    try:
        processor = get_subtitle_processor_instance()
        
        # 创建进度回调函数
        async def progress_callback(progress: float, message: str = ""):
            """进度回调函数"""
            try:
                # 确保进度在0-100范围内
                progress = max(0, min(100, progress))
                
                # 如果进度为0且包含"错误"字样，标记为失败
                if progress == 0 and ("错误" in message or "失败" in message):
                    await task_manager.update_task(
                        task_id, 
                        status='failed',
                        progress=0, 
                        error=message,
                        message=f"处理失败: {message}"
                    )
                else:
                    await task_manager.update_task(
                        task_id, 
                        progress=progress, 
                        message=message,
                        status='running' if progress < 100 else 'completed'
                    )
                    
                logger.debug(f"任务 {task_id} 进度更新: {progress}% - {message}")
            except Exception as e:
                logger.error(f"进度回调失败: {e}")
        
        # 更新任务状态
        await task_manager.update_task(task_id, status='running', progress=5, message='开始处理...')
        
        result = None
        
        if operation == 'generate_from_url':
            # 从URL生成字幕
            video_url = request.get('video_url')
            if not video_url:
                raise ValueError("缺少video_url参数")
            
            if not validate_url(video_url):
                raise ValueError("无效的视频URL")
            
            await progress_callback(10, '从URL生成字幕...')
            
            try:
                result = await processor.process_from_url(
                    video_url=video_url,
                    source_language=request.get('language', 'auto'),
                    model_size=request.get('model_size', 'large-v3'),
                    target_language=request.get('target_language'),
                    quality_mode=request.get('quality_mode', 'balance'),
                    task_id=task_id,
                    progress_callback=progress_callback  # 传递进度回调
                )
            except Exception as e:
                error_msg = f"URL处理异常: {str(e)}"
                logger.error(f"任务 {task_id} 执行失败: {error_msg}")
                await progress_callback(0, f"错误: {error_msg}")
                result = {"success": False, "error": error_msg}
            
        elif operation == 'generate_from_file':
            # 从文件生成字幕
            video_file_path = request.get('video_file_path')
            if not video_file_path:
                raise ValueError("缺少video_file_path参数")
            
            # 构建完整路径
            if not os.path.isabs(video_file_path):
                video_file_path = os.path.join(settings.FILES_PATH, video_file_path)
            
            if not os.path.exists(video_file_path):
                raise ValueError("视频文件不存在")
            
            # 获取原始文件标题
            original_title = get_original_title_from_file_path(video_file_path)
            logger.info(f"使用原始标题生成字幕: {original_title}")
            
            await progress_callback(10, '从文件生成字幕...')
            
            try:
                result = await processor.process_from_file(
                    video_file_path=video_file_path,
                    source_language=request.get('language', 'auto'),
                    model_size=request.get('model_size', 'large-v3'),
                    target_language=request.get('target_language'),
                    quality_mode=request.get('quality_mode', 'balance'),
                    task_id=task_id,
                    video_title=original_title,  # 传递原始标题
                    progress_callback=progress_callback  # 传递进度回调
                )
            except Exception as e:
                error_msg = f"文件处理异常: {str(e)}"
                logger.error(f"任务 {task_id} 执行失败: {error_msg}")
                await progress_callback(0, f"错误: {error_msg}")
                result = {"success": False, "error": error_msg}
            
        elif operation == 'translate':
            # 翻译字幕
            subtitle_file_path = request.get('subtitle_file_path')
            target_language = request.get('target_language')
            
            if not subtitle_file_path:
                raise ValueError("缺少subtitle_file_path参数")
            if not target_language:
                raise ValueError("缺少target_language参数")
            
            # 构建完整路径
            if not os.path.isabs(subtitle_file_path):
                subtitle_file_path = os.path.join(settings.FILES_PATH, subtitle_file_path)
            
            if not os.path.exists(subtitle_file_path):
                raise ValueError("字幕文件不存在")
            
            # 获取原始文件标题
            original_title = get_original_title_from_file_path(subtitle_file_path)
            logger.info(f"使用原始标题翻译字幕: {original_title}")
            
            await progress_callback(10, '翻译字幕...')
            
            try:
                result = await processor.translate_subtitle_file(
                    subtitle_path=subtitle_file_path,
                    source_language=request.get('source_language', 'auto'),
                    target_language=target_language,
                    translation_method=request.get('translation_method', 'optimized'),
                    quality_mode=request.get('quality_mode', 'balance'),
                    task_id=task_id,
                    original_title=original_title,  # 传递原始标题
                    progress_callback=progress_callback  # 传递进度回调
                )
            except Exception as e:
                error_msg = f"翻译处理异常: {str(e)}"
                logger.error(f"任务 {task_id} 执行失败: {error_msg}")
                await progress_callback(0, f"错误: {error_msg}")
                result = {"success": False, "error": error_msg}
            
        else:
            raise ValueError(f"不支持的操作类型: {operation}")
        
        # 处理结果
        if result and result.get('success'):
            await task_manager.update_task(
                task_id, 
                status='completed', 
                progress=100, 
                message='处理完成',
                result=result
            )
            logger.info(f"✅ 任务 {task_id} 成功完成")
        else:
            error_msg = result.get('error', '处理失败') if result else '未知错误'
            await task_manager.update_task(
                task_id,
                status='failed',
                progress=0,
                error=error_msg,
                message=f"处理失败: {error_msg}"
            )
            logger.error(f"❌ 任务 {task_id} 处理失败: {error_msg}")
            
    except Exception as e:
        error_msg = f"任务执行异常: {str(e)}"
        logger.error(f"❌ 任务 {task_id} 执行异常: {error_msg}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        
        # 确保失败状态被推送
        try:
            await task_manager.update_task(
                task_id,
                status='failed',
                progress=0,
                error=error_msg,
                message=f"执行异常: {error_msg}"
            )
        except Exception as update_error:
            logger.error(f"更新任务状态失败: {update_error}")

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        task_info = task_manager.get_task(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 计算运行时间
        elapsed_time = time.time() - task_info['start_time']
        
        response = {
            "task_id": task_id,
            "status": task_info['status'],
            "progress": task_info['progress'],
            "message": task_info['message'],
            "elapsed_time": elapsed_time
        }
        
        # 添加错误信息
        if task_info.get('error'):
            response['error'] = task_info['error']
        
        # 添加结果信息
        if task_info.get('result'):
            result = task_info['result']
            response['result'] = {
                'subtitle_file': result.get('subtitle_file'),
                'language': result.get('language'),
                'duration': result.get('duration'),
                'title': result.get('title'),
                'translated': result.get('translated', False),
                'target_language': result.get('target_language')
            }
            
            # 如果有字幕文件，生成下载信息
            if result.get('subtitle_file'):
                filename = os.path.basename(result['subtitle_file'])
                response['download_url'] = f"/api/v1/subtitles/download/{filename}"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@router.get("/download/{filename}")
async def download_subtitle_file(filename: str):
    """下载字幕文件"""
    try:
        file_path = os.path.join(settings.FILES_PATH, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 获取原始文件名
        original_filename = filename
        file_stem = Path(filename).stem
        
        # 尝试从映射文件获取原始标题
        try:
            mapping_file = os.path.join(settings.FILES_PATH, f"{file_stem}_mapping.json")
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_info = json.load(f)
                    original_title = mapping_info.get('original_title', file_stem)
                    file_ext = Path(filename).suffix
                    original_filename = f"{original_title}{file_ext}"
        except Exception:
            pass
        
        return FileResponse(
            path=file_path,
            filename=original_filename,
            media_type='text/plain'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        success = task_manager.cancel_task(task_id)
        
        if success:
            return {
                "success": True,
                "message": f"任务 {task_id} 已取消",
                "task_id": task_id
            }
        else:
            return {
                "success": False,
                "message": f"任务 {task_id} 不存在或无法取消",
                "task_id": task_id
            }
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.post("/cancel-task")
async def cancel_task_legacy(request: dict):
    """取消任务 - 兼容旧版本前端"""
    try:
        task_id = request.get('task_id')
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少task_id参数")
        
        # 调用已有的取消任务函数
        success = task_manager.cancel_task(task_id)
        
        if success:
            return {
                "success": True,
                "message": f"任务 {task_id} 已取消",
                "task_id": task_id
            }
        else:
            return {
                "success": False,
                "message": f"任务 {task_id} 不存在或无法取消",
                "task_id": task_id
            }
            
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.get("/config")
async def get_subtitle_config():
    """获取字幕处理配置信息"""
    try:
        processor = get_subtitle_processor_instance()
        
        return {
            "success": True,
            "config": {
                "supported_languages": processor.get_supported_languages(),
                "supported_models": processor.get_supported_models(),
                "quality_modes": processor.get_quality_modes(),
                "default_settings": {
                    "model": "large-v3",
                    "quality_mode": "balance",
                    "language": "auto"
                },
                "translation_methods": {
                    "optimized": "优化翻译器 (推荐)",
                    "enhanced": "增强翻译器",
                    "basic": "基础翻译器"
                },
                "supported_formats": {
                    "video": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"],
                    "subtitle": [".srt", ".vtt", ".ass", ".ssa", ".sub"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取配置信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.get("/tasks")
async def get_active_tasks():
    """获取所有活跃任务"""
    try:
        tasks = []
        for task_id, task_info in task_manager.tasks.items():
            elapsed_time = time.time() - task_info['start_time']
            tasks.append({
                "task_id": task_id,
                "operation": task_info['operation'],
                "status": task_info['status'],
                "progress": task_info['progress'],
                "message": task_info['message'],
                "elapsed_time": elapsed_time
            })
        
        return {
            "success": True,
            "tasks": tasks,
            "total": len(tasks)
        }
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@router.delete("/cleanup")
async def cleanup_completed_tasks():
    """清理已完成的任务"""
    try:
        completed_statuses = ['completed', 'failed', 'cancelled']
        task_ids_to_remove = [
            task_id for task_id, task_info in task_manager.tasks.items()
            if task_info['status'] in completed_statuses
        ]
        
        for task_id in task_ids_to_remove:
            task_manager.cleanup_task(task_id)
        
        return {
            "success": True,
            "message": f"清理了 {len(task_ids_to_remove)} 个已完成的任务",
            "cleaned_tasks": len(task_ids_to_remove)
        }
        
    except Exception as e:
        logger.error(f"清理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

# 兼容性接口 - 保持与旧版本的兼容
@router.post("/generate-from-url")
async def generate_from_url_compat(request: dict):
    """兼容性接口：从URL生成字幕"""
    request['operation'] = 'generate_from_url'
    return await process_subtitle(request)

@router.post("/generate-from-file")
async def generate_from_file_compat(request: dict):
    """兼容性接口：从文件生成字幕"""
    request['operation'] = 'generate_from_file'
    return await process_subtitle(request)

@router.post("/translate-subtitle")
async def translate_subtitle_compat(request: dict):
    """兼容性接口：翻译字幕"""
    request['operation'] = 'translate'
    return await process_subtitle(request)
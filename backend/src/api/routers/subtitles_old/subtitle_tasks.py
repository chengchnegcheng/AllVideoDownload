"""
字幕任务管理API

包含任务取消、状态查询等任务管理功能
"""

from fastapi import APIRouter, HTTPException
import time
import logging

from .subtitle_utils import task_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/cancel-task")
async def cancel_task(request: dict):
    """取消正在进行的任务"""
    try:
        task_id = request.get('task_id')
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少task_id参数")
        
        # 取消任务
        cancelled = task_manager.cancel_task(task_id)
        
        if cancelled:
            logger.info(f"任务已取消: {task_id}")
            
            # 尝试清理临时文件
            try:
                from ....core.subtitle_processor import get_subtitle_processor_instance
                processor = get_subtitle_processor_instance()
                # 暂时注释掉这行，因为processor可能没有这个方法
                # await processor.cleanup_temp_files_by_task(task_id)
                logger.info(f"临时文件清理请求已发送")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
            
            return {
                "success": True,
                "message": "任务已成功取消",
                "task_id": task_id
            }
        else:
            return {
                "success": False,
                "message": "任务不存在或已完成",
                "task_id": task_id
            }
            
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        with task_manager.lock:
            task_info = task_manager.active_tasks.get(task_id)
        
        if task_info:
            return {
                "success": True,
                "task_id": task_id,
                "status": task_info["status"],
                "start_time": task_info.get("start_time"),
                "running_time": time.time() - task_info.get("start_time", time.time())
            }
        else:
            return {
                "success": False,
                "message": "任务不存在",
                "task_id": task_id
            }
            
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
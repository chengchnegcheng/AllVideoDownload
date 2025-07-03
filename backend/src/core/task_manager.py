#!/usr/bin/env python3
"""
后台任务管理器

实现字幕处理任务的持久化运行：
1. 任务在后台独立运行，不受前端连接影响
2. 前端可以随时重连获取任务状态
3. 保持原始文件名
4. 自动清理完成的任务
"""

import asyncio
import uuid
import time
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待开始
    RUNNING = "running"      # 正在运行
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"       # 失败
    CANCELLED = "cancelled" # 已取消

class TaskType(Enum):
    """任务类型枚举"""
    GENERATE_URL = "generate_url"        # 从URL生成字幕
    GENERATE_FILE = "generate_file"      # 从文件生成字幕
    TRANSLATE = "translate"              # 翻译字幕
    BURN = "burn"                       # 烧录字幕

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # 任务参数
    params: Dict[str, Any] = None
    
    # 原始文件信息
    original_filename: Optional[str] = None
    
    # 结果信息
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # 文件路径
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换枚举为字符串
        data['status'] = self.status.value
        data['task_type'] = self.task_type.value
        return data

class BackgroundTaskManager:
    """后台任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.cleanup_interval = 3600  # 1小时清理一次完成的任务
        self._start_cleanup_task()
        
        logger.info("后台任务管理器初始化完成")
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        def cleanup_loop():
            while True:
                try:
                    self._cleanup_old_tasks()
                    time.sleep(self.cleanup_interval)
                except Exception as e:
                    logger.error(f"清理任务失败: {e}")
                    time.sleep(60)  # 出错后等待1分钟再试
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_old_tasks(self):
        """清理旧任务"""
        current_time = time.time()
        tasks_to_remove = []
        
        for task_id, task_info in self.tasks.items():
            # 清理24小时前完成的任务
            if (task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task_info.completed_at and current_time - task_info.completed_at > 86400):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            if task_id in self.tasks:
                del self.tasks[task_id]
                logger.info(f"清理旧任务: {task_id}")
        
        logger.info(f"任务清理完成，清理了 {len(tasks_to_remove)} 个旧任务")
    
    def create_task(self, 
                   task_type: TaskType, 
                   params: Dict[str, Any],
                   original_filename: Optional[str] = None) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=time.time(),
            params=params or {},
            original_filename=original_filename
        )
        
        self.tasks[task_id] = task_info
        logger.info(f"创建任务: {task_id} ({task_type.value})")
        
        return task_id
    
    async def start_task(self, task_id: str, task_func: Callable, **kwargs):
        """启动任务"""
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")
        
        task_info = self.tasks[task_id]
        if task_info.status != TaskStatus.PENDING:
            raise ValueError(f"任务状态错误: {task_info.status}")
        
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = time.time()
        task_info.message = "任务开始运行..."
        
        # 创建进度回调
        async def progress_callback(progress: float, message: str = ""):
            if task_id in self.tasks:
                self.tasks[task_id].progress = max(0, min(100, progress))
                self.tasks[task_id].message = message
                logger.debug(f"任务 {task_id} 进度: {progress}% - {message}")
        
        # 启动后台任务
        async def run_task():
            try:
                logger.info(f"开始执行任务: {task_id}")
                
                # 执行任务函数，传入进度回调
                result = await task_func(progress_callback=progress_callback, **kwargs)
                
                # 更新任务状态
                if result.get('success'):
                    task_info.status = TaskStatus.COMPLETED
                    task_info.progress = 100.0
                    task_info.message = "任务完成！"
                    task_info.result = result
                    
                    # 生成下载文件名，保持原始文件名
                    if task_info.original_filename and result.get('subtitle_file'):
                        original_name = Path(task_info.original_filename).stem
                        extension = Path(result['subtitle_file']).suffix or '.srt'
                        download_filename = f"{original_name}_subtitles{extension}"
                        task_info.result['download_filename'] = download_filename
                    
                    logger.info(f"任务完成: {task_id}")
                else:
                    task_info.status = TaskStatus.FAILED
                    task_info.error = result.get('error', '未知错误')
                    logger.error(f"任务失败: {task_id} - {task_info.error}")
                
            except asyncio.CancelledError:
                task_info.status = TaskStatus.CANCELLED
                task_info.message = "任务已取消"
                logger.info(f"任务被取消: {task_id}")
                raise
            except Exception as e:
                task_info.status = TaskStatus.FAILED
                task_info.error = str(e)
                task_info.message = f"任务执行失败: {str(e)}"
                logger.error(f"任务执行异常: {task_id} - {e}")
            finally:
                task_info.completed_at = time.time()
                # 清理运行中的任务记录
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
        
        # 启动后台任务
        background_task = asyncio.create_task(run_task())
        self.running_tasks[task_id] = background_task
        
        logger.info(f"任务已启动: {task_id}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        
        return self.tasks[task_id].to_dict()
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        return [task.to_dict() for task in self.tasks.values()]
    
    def get_running_tasks(self) -> List[Dict[str, Any]]:
        """获取正在运行的任务"""
        return [task.to_dict() for task in self.tasks.values() 
                if task.status == TaskStatus.RUNNING]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.tasks:
            return False
        
        task_info = self.tasks[task_id]
        
        if task_info.status != TaskStatus.RUNNING:
            return False
        
        # 取消后台任务
        if task_id in self.running_tasks:
            background_task = self.running_tasks[task_id]
            background_task.cancel()
            
            try:
                await background_task
            except asyncio.CancelledError:
                pass
        
        task_info.status = TaskStatus.CANCELLED
        task_info.completed_at = time.time()
        task_info.message = "任务已取消"
        
        logger.info(f"任务已取消: {task_id}")
        return True
    
    def cleanup_task(self, task_id: str):
        """清理指定任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"清理任务: {task_id}")
    
    def get_task_file(self, task_id: str) -> Optional[str]:
        """获取任务结果文件路径"""
        task_info = self.tasks.get(task_id)
        if not task_info or task_info.status != TaskStatus.COMPLETED:
            return None
        
        result = task_info.result
        if not result:
            return None
        
        return result.get('subtitle_file') or result.get('output_file')
    
    def get_task_download_info(self, task_id: str) -> Optional[Dict[str, str]]:
        """获取任务下载信息"""
        task_info = self.tasks.get(task_id)
        if not task_info or task_info.status != TaskStatus.COMPLETED:
            return None
        
        result = task_info.result
        if not result:
            return None
        
        file_path = result.get('subtitle_file') or result.get('output_file')
        if not file_path:
            return None
        
        # 生成下载文件名
        if task_info.original_filename:
            original_name = Path(task_info.original_filename).stem
            extension = Path(file_path).suffix or '.srt'
            download_filename = f"{original_name}_subtitles{extension}"
        else:
            download_filename = Path(file_path).name
        
        return {
            'file_path': file_path,
            'download_filename': download_filename
        }

# 全局任务管理器实例
_task_manager_instance = None

def get_task_manager() -> BackgroundTaskManager:
    """获取任务管理器单例"""
    global _task_manager_instance
    if _task_manager_instance is None:
        _task_manager_instance = BackgroundTaskManager()
    return _task_manager_instance

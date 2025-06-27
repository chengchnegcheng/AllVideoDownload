"""
字幕处理相关的工具类和函数

包含任务管理、文件名处理等通用功能
"""

import threading
import time
import re
import os
from pathlib import Path
from typing import Optional


class TaskManager:
    """任务管理器，用于跟踪和管理正在进行的任务"""
    
    def __init__(self):
        self.active_tasks = {}
        self.lock = threading.Lock()
    
    def start_task(self, task_id: str, thread_obj=None):
        """启动任务"""
        with self.lock:
            self.active_tasks[task_id] = {
                "status": "running",
                "start_time": time.time(),
                "thread": thread_obj
            }
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        with self.lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                return True
            return False
    
    def complete_task(self, task_id: str):
        """完成任务"""
        with self.lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def is_cancelled(self, task_id: str):
        """检查任务是否被取消"""
        with self.lock:
            return task_id not in self.active_tasks
    
    def cleanup_task(self, task_id: str):
        """清理任务"""
        self.complete_task(task_id)
    
    def get_active_tasks(self):
        """获取活动任务列表"""
        with self.lock:
            return list(self.active_tasks.keys())


# 全局任务管理器实例
task_manager = TaskManager()


def validate_url(url: str) -> bool:
    """验证URL格式"""
    if not url:
        return False
    
    # 简单的URL验证
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def get_original_title_from_path(file_path: str) -> str:
    """从文件路径获取原始标题"""
    try:
        file_name = Path(file_path).name
        
        # 检查是否是UUID格式的文件名
        if len(file_name.split('.')[0]) == 36 and '-' in file_name:
            # 这是一个UUID文件名，尝试查找相关的原始文件名
            directory = Path(file_path).parent
            uuid_part = file_name.split('.')[0]
            
            # 查找映射文件
            mapping_file = directory / f"{uuid_part}_mapping.json"
            if mapping_file.exists():
                try:
                    import json
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping = json.load(f)
                        return mapping.get('original_filename', file_name)
                except Exception:
                    pass
            
            # 如果没有映射文件，尝试在同目录中查找相关的视频文件
            related_title = find_related_video_title(str(directory), uuid_part)
            if related_title:
                return related_title
        
        # 移除文件扩展名并返回
        return Path(file_name).stem
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"无法从路径提取标题: {e}")
        return "未知标题"


def find_related_video_title(directory: str, exclude_uuid: str) -> str:
    """在指定目录中查找相关的视频文件标题"""
    try:
        from ....core.config import settings
        
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        
        for file_path in Path(directory).iterdir():
            if file_path.is_file():
                # 跳过UUID文件
                if exclude_uuid in file_path.name:
                    continue
                
                # 检查是否是视频文件
                if file_path.suffix.lower() in video_extensions:
                    return file_path.stem
        
        return None
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"查找相关视频标题失败: {e}")
        return None


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不安全字符"""
    safe_chars = re.sub(r'[<>:"/\\|?*]', '', filename)
    safe_chars = re.sub(r'\s+', ' ', safe_chars).strip()
    
    if not safe_chars:
        return "subtitle"
    
    # 限制文件名长度
    if len(safe_chars.encode('utf-8')) > 200:
        result_name = ""
        for char in safe_chars:
            test_result = result_name + char
            if len(test_result.encode('utf-8')) > 200:
                break
            result_name = test_result
        safe_chars = result_name.strip()
        if not safe_chars:
            return "subtitle"
    
    return safe_chars


def encode_filename_for_download(filename: str) -> str:
    """为下载编码文件名"""
    try:
        filename.encode('ascii')
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        try:
            import urllib.parse
            encoded_filename = urllib.parse.quote(filename, safe='')
            ascii_safe = re.sub(r'[^\w\.-]', '_', filename, flags=re.ASCII)
            ascii_safe = re.sub(r'_+', '_', ascii_safe).strip('_')
            
            if not ascii_safe.endswith('.srt'):
                ascii_safe = ascii_safe.rstrip('.') + '.srt'
            
            return f'attachment; filename="{ascii_safe}"; filename*=UTF-8\'\'{encoded_filename}'
        except Exception:
            return f'attachment; filename="subtitle_download.srt"' 
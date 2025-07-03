
import asyncio
import json
from typing import Callable, Optional
import queue
import threading
import time

class ProgressHandler:
    """改进的进度处理器，解决前后端同步问题"""
    
    def __init__(self):
        self.progress_queue = asyncio.Queue()
        self.current_progress = 0
        self.current_message = ""
        self.is_active = False
        
    async def update_progress(self, progress: float, message: str = ""):
        """更新进度（线程安全）"""
        # 确保进度在合理范围内
        progress = max(0, min(100, progress))
        
        # 只有进度有变化才更新
        if abs(progress - self.current_progress) >= 0.1 or message != self.current_message:
            self.current_progress = progress
            self.current_message = message
            
            if self.is_active:
                await self.progress_queue.put({
                    'progress': progress,
                    'message': message,
                    'timestamp': time.time()
                })
    
    async def get_progress_stream(self):
        """获取进度流式数据"""
        self.is_active = True
        
        try:
            while self.is_active:
                try:
                    # 等待进度更新
                    data = await asyncio.wait_for(self.progress_queue.get(), timeout=1.0)
                    
                    # 格式化为SSE数据
                    sse_data = {
                        'status': 'processing',
                        'progress': round(data['progress'], 1),
                        'message': data['message'],
                        'timestamp': data['timestamp']
                    }
                    
                    yield f"data: {json.dumps(sse_data)}\n\n"
                    
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    heartbeat = {
                        'status': 'heartbeat',
                        'progress': self.current_progress,
                        'message': self.current_message,
                        'timestamp': time.time()
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                    
        finally:
            self.is_active = False
    
    def stop(self):
        """停止进度处理"""
        self.is_active = False

# 使用示例
async def example_usage():
    progress_handler = ProgressHandler()
    
    # 启动进度流
    async def progress_stream():
        async for data in progress_handler.get_progress_stream():
            print(data.strip())  # 在实际使用中这里是yield到客户端
    
    # 模拟任务进度
    async def simulate_task():
        for i in range(101):
            await progress_handler.update_progress(i, f"处理进度 {i}%")
            await asyncio.sleep(0.1)
        
        progress_handler.stop()
    
    # 并发运行
    await asyncio.gather(
        progress_stream(),
        simulate_task()
    )

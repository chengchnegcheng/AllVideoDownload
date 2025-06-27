"""
AVD Web版本 - WebSocket管理器

管理WebSocket连接，用于实时推送下载进度和状态更新
"""

import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket
import asyncio

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_ids: Dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, connection_id: str = None):
        """接受WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            connection_id: 连接ID（可选）
        """
        try:
            await websocket.accept()
            
            async with self._lock:
                self.active_connections.append(websocket)
                if connection_id:
                    self.connection_ids[websocket] = connection_id
            
            logger.info(f"WebSocket连接已建立，当前活跃连接数: {len(self.active_connections)}")
            
            # 发送连接成功消息
            await self.send_personal_message({
                "type": "connection_established",
                "message": "WebSocket连接成功",
                "connection_id": connection_id
            }, websocket)
            
        except Exception as e:
            logger.error(f"建立WebSocket连接失败: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
        """
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            
            if websocket in self.connection_ids:
                del self.connection_ids[websocket]
            
            logger.info(f"WebSocket连接已断开，当前活跃连接数: {len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"断开WebSocket连接失败: {e}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送消息给特定连接
        
        Args:
            message: 要发送的消息
            websocket: 目标WebSocket连接
        """
        try:
            if websocket in self.active_connections:
                message_str = json.dumps(message, ensure_ascii=False)
                await websocket.send_text(message_str)
            
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            # 如果发送失败，移除连接
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接
        
        Args:
            message: 要广播的消息
        """
        if not self.active_connections:
            return
        
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected_connections.append(connection)
        
        # 清理断开的连接
        for connection in disconnected_connections:
            self.disconnect(connection)
    
    async def send_to_connection_id(self, message: Dict[str, Any], connection_id: str):
        """发送消息给特定连接ID
        
        Args:
            message: 要发送的消息
            connection_id: 目标连接ID
        """
        target_websocket = None
        
        for websocket, cid in self.connection_ids.items():
            if cid == connection_id:
                target_websocket = websocket
                break
        
        if target_websocket:
            await self.send_personal_message(message, target_websocket)
        else:
            logger.warning(f"未找到连接ID: {connection_id}")
    
    async def send_download_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """发送下载进度更新
        
        Args:
            task_id: 任务ID
            progress_data: 进度数据
        """
        message = {
            "type": "download_progress",
            "task_id": task_id,
            "data": progress_data,
            "timestamp": progress_data.get("timestamp")
        }
        
        await self.broadcast(message)
    
    async def send_download_completed(self, task_id: str, result_data: Dict[str, Any]):
        """发送下载完成通知
        
        Args:
            task_id: 任务ID
            result_data: 结果数据
        """
        message = {
            "type": "download_completed",
            "task_id": task_id,
            "data": result_data,
            "timestamp": result_data.get("timestamp")
        }
        
        await self.broadcast(message)
    
    async def send_download_failed(self, task_id: str, error_data: Dict[str, Any]):
        """发送下载失败通知
        
        Args:
            task_id: 任务ID
            error_data: 错误数据
        """
        message = {
            "type": "download_failed",
            "task_id": task_id,
            "data": error_data,
            "timestamp": error_data.get("timestamp")
        }
        
        await self.broadcast(message)
    
    async def send_subtitle_progress(self, task_id: str, progress_data: Dict[str, Any]):
        """发送字幕处理进度更新
        
        Args:
            task_id: 任务ID
            progress_data: 进度数据
        """
        message = {
            "type": "subtitle_progress",
            "task_id": task_id,
            "data": progress_data,
            "timestamp": progress_data.get("timestamp")
        }
        
        await self.broadcast(message)
    
    async def send_system_notification(self, notification: Dict[str, Any]):
        """发送系统通知
        
        Args:
            notification: 通知数据
        """
        message = {
            "type": "system_notification",
            "data": notification,
            "timestamp": notification.get("timestamp")
        }
        
        await self.broadcast(message)
    
    async def send_message(self, message: Dict[str, Any]):
        """通用消息发送方法
        
        Args:
            message: 要发送的消息
        """
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """获取当前活跃连接数
        
        Returns:
            活跃连接数量
        """
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息
        
        Returns:
            连接信息字典
        """
        return {
            "active_connections": len(self.active_connections),
            "connection_ids": list(self.connection_ids.values()),
            "status": "healthy" if self.active_connections else "no_connections"
        }
    
    async def ping_all_connections(self):
        """向所有连接发送ping消息
        
        用于保持连接活跃和检测断开的连接
        """
        if not self.active_connections:
            return
        
        ping_message = {
            "type": "ping",
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.broadcast(ping_message)
    
    async def cleanup_inactive_connections(self):
        """清理不活跃的连接"""
        inactive_connections = []
        
        for connection in self.active_connections:
            try:
                # 尝试发送ping来检测连接状态
                await connection.ping()
            except Exception:
                inactive_connections.append(connection)
        
        # 移除不活跃的连接
        for connection in inactive_connections:
            self.disconnect(connection)
        
        if inactive_connections:
            logger.info(f"已清理 {len(inactive_connections)} 个不活跃的连接")

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager() 
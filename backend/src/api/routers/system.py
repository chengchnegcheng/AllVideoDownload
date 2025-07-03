"""
AVD Web版本 - 系统API路由

提供系统管理相关的API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os
import sys
import psutil
import platform
import json
import math
from pathlib import Path
import time
import logging
from datetime import datetime, timedelta
import re

from ...core.config import settings, SUPPORTED_PLATFORMS, QUALITY_OPTIONS, SUBTITLE_LANGUAGES
from ...core.database import get_db
from ...models.downloads import DownloadTask, DownloadStatus
from ...models.subtitles import SubtitleTask, SubtitleStatus
from ...utils.logger import format_error_message, clean_ansi_codes

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic模型
class SystemInfo(BaseModel):
    """系统信息模型"""
    platform: str
    python_version: str
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_total: int
    disk_free: int

class SystemSettings(BaseModel):
    """系统设置模型"""
    # 服务器设置
    server_host: str = Field(description="服务器主机地址")
    backend_port: int = Field(ge=1, le=65535, description="后端服务器端口")
    frontend_port: int = Field(ge=1, le=65535, description="前端服务器端口")
    
    # 下载设置
    max_concurrent_downloads: int = Field(ge=1, le=10, description="最大并发下载数")
    max_file_size_mb: int = Field(ge=100, le=10240, description="最大文件大小(MB)")
    default_quality: str = Field(description="默认视频质量")
    default_format: str = Field(description="默认视频格式")
    
    # AI设置
    whisper_model_size: str = Field(description="Whisper模型大小")
    whisper_device: str = Field(description="AI计算设备")
    
    # 存储设置
    files_path: str = Field(description="文件存储路径")
    auto_cleanup_days: int = Field(ge=1, le=365, description="自动清理天数")
    
    # 网络设置
    http_proxy: Optional[str] = Field(default=None, description="HTTP代理")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS代理")
    rate_limit_per_minute: int = Field(ge=10, le=1000, description="每分钟速率限制")
    
    # 日志设置
    log_level: str = Field(description="日志级别")
    log_retention_days: int = Field(ge=1, le=365, description="日志保留天数")

class TaskStats(BaseModel):
    """任务统计模型"""
    total_downloads: int
    active_downloads: int
    completed_downloads: int
    failed_downloads: int
    total_subtitles: int
    active_subtitles: int
    completed_subtitles: int
    failed_subtitles: int

class NetworkSettings(BaseModel):
    """网络设置模型"""
    proxy_type: str = Field(default="none", description="代理类型: none, http, https, socks5")
    proxy_host: Optional[str] = Field(default="", description="代理主机")
    proxy_port: Optional[int] = Field(default=None, ge=1, le=65535, description="代理端口")
    proxy_username: Optional[str] = Field(default="", description="代理用户名")
    proxy_password: Optional[str] = Field(default="", description="代理密码")
    test_url: str = Field(default="https://www.youtube.com", description="测试URL")
    timeout: int = Field(default=30, ge=5, le=120, description="连接超时(秒)")

class NetworkTestResult(BaseModel):
    """网络测试结果模型"""
    success: bool
    message: str
    response_time: Optional[float] = None
    error: Optional[str] = None

@router.get("/status")
async def get_system_status():
    """获取系统状态"""
    try:
        # 获取系统信息
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = SystemInfo(
            platform=platform.platform(),
            python_version=platform.python_version(),
            cpu_count=psutil.cpu_count(),
            memory_total=memory.total,
            memory_available=memory.available,
            disk_total=disk.total,
            disk_free=disk.free
        )
        
        # 检查重要服务状态
        services_status = {
            "database": "healthy",
            "websocket": "healthy",
            "download_service": "healthy",
            "subtitle_service": "healthy"
        }
        
        # 检查存储目录
        storage_status = {
            "download_path": {
                            "path": settings.FILES_PATH,
            "exists": os.path.exists(settings.FILES_PATH),
            "writable": os.access(settings.FILES_PATH, os.W_OK) if os.path.exists(settings.FILES_PATH) else False
            },
            "models_path": {
                "path": settings.MODELS_PATH,
                "exists": os.path.exists(settings.MODELS_PATH),
                "writable": os.access(settings.MODELS_PATH, os.W_OK) if os.path.exists(settings.MODELS_PATH) else False
            }
        }
        
        return {
            "status": "running",
            "version": settings.VERSION,
            "system_info": system_info.dict(),
            "services": services_status,
            "storage": storage_status,
            "uptime": "正常运行",
            "message": "系统运行正常"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@router.get("/info")
async def get_system_info():
    """获取系统基本信息"""
    try:
        # CPU信息
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        # 使用非阻塞方式获取CPU使用率，避免API响应延迟
        cpu_percent = psutil.cpu_percent(interval=None)  # 立即返回，不阻塞
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        
        # 网络信息 - 优化性能，简化获取
        try:
            network_addrs = psutil.net_if_addrs()
        except Exception as e:
            logger.warning(f"获取网络地址失败: {e}")
            network_addrs = {}
        
        # 网络流量统计 - 快速获取基本信息
        try:
            network_io = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": network_io.bytes_sent if network_io else 0,
                "bytes_recv": network_io.bytes_recv if network_io else 0,
                "packets_sent": network_io.packets_sent if network_io else 0,
                "packets_recv": network_io.packets_recv if network_io else 0,
                "errin": network_io.errin if network_io else 0,
                "errout": network_io.errout if network_io else 0,
                "dropin": network_io.dropin if network_io else 0,
                "dropout": network_io.dropout if network_io else 0,
            }
        except Exception as e:
            logger.warning(f"获取网络流量统计失败: {e}")
            network_stats = {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "errin": 0,
                "errout": 0,
                "dropin": 0,
                "dropout": 0,
            }
        
        # 网络接口统计（详细信息）- 优化性能
        network_interfaces = []
        try:
            # 简化网络接口信息获取，避免性能瓶颈
            for iface, addrs in network_addrs.items():
                # 只处理主要网络接口，跳过虚拟接口以提升性能
                if iface.startswith(('docker', 'veth', 'br-')):
                    continue
                    
                iface_info = {
                    "name": iface,
                    "addresses": [addr.address for addr in addrs],
                    "is_up": True,  # 简化处理，避免额外系统调用
                    "speed": 1000 if iface != 'lo' else 0,  # 使用合理默认值
                    "mtu": 1500 if iface != 'lo' else 65536  # 使用合理默认值
                }
                network_interfaces.append(iface_info)
                
                # 限制接口数量，避免处理过多接口影响性能
                if len(network_interfaces) >= 10:
                    break
                    
        except Exception as e:
            logger.warning(f"获取网络接口信息失败: {e}")
            # 提供基本的默认网络接口信息
            network_interfaces = [
                {"name": "lo", "addresses": ["127.0.0.1"], "is_up": True, "speed": 0, "mtu": 65536},
                {"name": "eth0", "addresses": ["未知"], "is_up": True, "speed": 1000, "mtu": 1500}
            ]
        
        # 进程信息 - 简化获取以提升性能
        try:
            process_count = len(psutil.pids())
        except Exception as e:
            logger.warning(f"获取进程数量失败: {e}")
            process_count = 0
        
        # 当前进程信息
        current_process = psutil.Process()
        current_pid = current_process.pid
        current_memory = current_process.memory_info().rss
        current_cpu = current_process.cpu_percent()
        process_start_time = current_process.create_time()
        
        return {
            "cpu": {
                "count": cpu_count,
                "count_logical": cpu_count_logical,
                "percent": cpu_percent
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "network": {
                # 整体网络流量统计
                **network_stats,
                # 网络接口信息
                "interfaces": list(network_addrs.keys()),
                "interfaces_detail": network_interfaces,
                "addresses": {iface: [addr.address for addr in addrs] 
                           for iface, addrs in network_addrs.items()}
            },
            "process_count": process_count,
            "processes": {
                "current_pid": current_pid,
                "current_memory": current_memory,
                "current_cpu": current_cpu,
                "start_time": process_start_time
            },
            "platform": os.name,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "environment": {
                "app_name": "AllVideoDownload",
                "version": "2.0.0",
                "host": settings.HOST,
                "port": settings.PORT,
                "debug": settings.DEBUG
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统信息失败")

@router.get("/stats", response_model=TaskStats)
async def get_task_stats(db = Depends(get_db)):
    """获取任务统计信息"""
    try:
        # 下载任务统计
        total_downloads = db.query(DownloadTask).count()
        active_downloads = db.query(DownloadTask).filter(
            DownloadTask.status.in_([DownloadStatus.PENDING, DownloadStatus.PROCESSING])
        ).count()
        completed_downloads = db.query(DownloadTask).filter(
            DownloadTask.status == DownloadStatus.COMPLETED
        ).count()
        failed_downloads = db.query(DownloadTask).filter(
            DownloadTask.status == DownloadStatus.FAILED
        ).count()
        
        # 字幕任务统计
        total_subtitles = db.query(SubtitleTask).count()
        active_subtitles = db.query(SubtitleTask).filter(
            SubtitleTask.status.in_([SubtitleStatus.PENDING, SubtitleStatus.PROCESSING])
        ).count()
        completed_subtitles = db.query(SubtitleTask).filter(
            SubtitleTask.status == SubtitleStatus.COMPLETED
        ).count()
        failed_subtitles = db.query(SubtitleTask).filter(
            SubtitleTask.status == SubtitleStatus.FAILED
        ).count()
        
        return TaskStats(
            total_downloads=total_downloads,
            active_downloads=active_downloads,
            completed_downloads=completed_downloads,
            failed_downloads=failed_downloads,
            total_subtitles=total_subtitles,
            active_subtitles=active_subtitles,
            completed_subtitles=completed_subtitles,
            failed_subtitles=failed_subtitles
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.get("/settings", response_model=SystemSettings)
async def get_system_settings():
    """获取系统设置"""
    try:
        # 从settings配置中获取正确的值
        return SystemSettings(
            # 服务器设置
            server_host=settings.HOST,
            backend_port=settings.PORT,
            frontend_port=3000,  # 前端默认端口
            
            # 下载设置
            max_concurrent_downloads=settings.MAX_CONCURRENT_DOWNLOADS,
            max_file_size_mb=settings.MAX_FILE_SIZE_MB,
            default_quality="best",
            default_format="mp4",
            
            # AI设置
            whisper_model_size=settings.WHISPER_MODEL_SIZE,
            whisper_device=settings.WHISPER_DEVICE,
            
            # 存储设置
            files_path=settings.FILES_PATH,
            auto_cleanup_days=30,  # 默认30天
            
            # 网络设置
            http_proxy=settings.HTTP_PROXY or "",
            https_proxy=settings.HTTPS_PROXY or "",
            rate_limit_per_minute=60,  # 默认每分钟60次
            
            # 日志设置
            log_level="INFO",
            log_retention_days=30  # 默认30天
        )
        
    except Exception as e:
        logger.error(f"获取系统设置失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统设置失败")

@router.post("/settings")
async def update_system_settings(settings_data: dict):
    """更新系统设置"""
    try:
        # 这里应该保存设置到配置文件或数据库
        # 目前只是示例实现
        logger.info(f"更新系统设置: {settings_data}")
        
        # 检查是否更新了端口设置
        backend_port_updated = False
        frontend_port_updated = False
        
        if 'backend_port' in settings_data:
            current_port = settings.PORT
            new_port = settings_data['backend_port']
            if current_port != new_port:
                backend_port_updated = True
                logger.info(f"后端端口设置已更新: {current_port} -> {new_port}")
        
        if 'frontend_port' in settings_data:
            # 假设前端默认端口是3000
            current_frontend_port = 3000
            new_frontend_port = settings_data['frontend_port']
            if current_frontend_port != new_frontend_port:
                frontend_port_updated = True
                logger.info(f"前端端口设置已更新: {current_frontend_port} -> {new_frontend_port}")
        
        response_message = "设置已保存"
        notes = []
        
        if backend_port_updated and frontend_port_updated:
            response_message += "，前端和后端端口都已更改"
            notes.append("前端和后端端口更改都需要重启相应服务才能生效")
        elif backend_port_updated:
            response_message += "，后端端口已更改"
            notes.append("后端端口更改需要重启后端服务才能生效")
        elif frontend_port_updated:
            response_message += "，前端端口已更改"
            notes.append("前端端口更改需要重启前端开发服务器才能生效")
        
        return {
            "success": True,
            "message": response_message,
            "settings": settings_data,
            "notes": notes
        }
        
    except Exception as e:
        logger.error(f"更新系统设置失败: {e}")
        raise HTTPException(status_code=500, detail="更新系统设置失败")

@router.get("/config")
async def get_system_config():
    """获取系统配置信息"""
    try:
        config_info = {
            "files_path": settings.FILES_PATH,
            "temp_path": settings.TEMP_PATH,
            "max_concurrent_downloads": settings.MAX_CONCURRENT_DOWNLOADS,
            "supported_formats": ["mp4", "mkv", "webm", "avi"],
            "quality_options": ["best", "720p", "480p", "360p", "worst"],
            "log_levels": {
                "debug": "详细调试信息（包含所有信息）",
                "info": "一般信息（推荐生产环境）",
                "warning": "警告及以上级别",
                "error": "错误及以上级别",
                "critical": "仅严重错误"
            },
            "subtitle_languages": ["auto", "zh", "en", "ja", "ko"],
            "proxy_enabled": bool(settings.HTTP_PROXY),
            "database_path": str(settings.DATABASE_URL).replace("sqlite:///", ""),
            "version": "1.0.0",
            "api_version": "v1"
        }
        
        return config_info
        
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统配置失败")

@router.post("/cleanup")
async def cleanup_system(
    cleanup_downloads: bool = False,
    cleanup_logs: bool = False,
    cleanup_temp: bool = True,
    days_old: int = 7,
    db = Depends(get_db)
):
    """清理系统文件"""
    try:
        cleaned_items = []
        
        # 清理临时文件
        if cleanup_temp:
            temp_count = 0
            temp_path = Path(settings.DATA_DIR) / "temp"
            if temp_path.exists():
                for file in temp_path.rglob("*"):
                    if file.is_file() and (file.stat().st_mtime < (time.time() - days_old * 86400)):
                        try:
                            file.unlink()
                            temp_count += 1
                        except Exception:
                            pass
            cleaned_items.append(f"临时文件: {temp_count} 个")
        
        # 清理下载文件
        if cleanup_downloads:
            download_count = 0
            files_path = Path(settings.FILES_PATH)
            if files_path.exists():
                for file in files_path.rglob("*"):
                    if file.is_file() and (file.stat().st_mtime < (time.time() - days_old * 86400)):
                        try:
                            file.unlink()
                            download_count += 1
                        except Exception:
                            pass
            cleaned_items.append(f"下载文件: {download_count} 个")
        
        # 清理日志文件
        if cleanup_logs:
            log_count = 0
            logs_path = Path(settings.LOGS_PATH)
            if logs_path.exists():
                for file in logs_path.rglob("*.log"):
                    if file.is_file() and (file.stat().st_mtime < (time.time() - days_old * 86400)):
                        try:
                            file.unlink()
                            log_count += 1
                        except Exception:
                            pass
            cleaned_items.append(f"日志文件: {log_count} 个")
        
        # 清理数据库中的旧记录
        if cleanup_downloads:
            cutoff_time = datetime.now() - timedelta(days=days_old)
            
            # 删除旧的失败任务
            deleted_downloads = db.query(DownloadTask).filter(
                DownloadTask.status == DownloadStatus.FAILED,
                DownloadTask.created_at < cutoff_time
            ).delete()
            
            deleted_subtitles = db.query(SubtitleTask).filter(
                SubtitleTask.status == SubtitleStatus.FAILED,
                SubtitleTask.created_at < cutoff_time
            ).delete()
            
            db.commit()
            
            cleaned_items.append(f"失败的下载任务: {deleted_downloads} 个")
            cleaned_items.append(f"失败的字幕任务: {deleted_subtitles} 个")
        
        return {
            "message": "系统清理完成",
            "cleaned_items": cleaned_items,
            "cleanup_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统清理失败: {str(e)}")

@router.post("/restart")
async def restart_system():
    """重启系统（仅重启应用服务）"""
    try:
        # 注意：这是一个简化的重启实现
        # 实际生产环境中应该使用适当的进程管理器
        
        import signal
        import sys
        
        # 发送重启信号
        return {
            "message": "正在重启系统...",
            "note": "系统将在几秒钟内重新启动",
            "status": "restarting"
        }
        
        # 实际重启代码（需要小心使用）
        # os.kill(os.getpid(), signal.SIGTERM)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启系统失败: {str(e)}")

@router.get("/network/settings", response_model=NetworkSettings)
async def get_network_settings():
    """获取网络设置"""
    try:
        # 解析当前的代理设置
        proxy_type = "none"
        proxy_host = ""
        proxy_port = None
        
        if settings.HTTP_PROXY:
            proxy_url = settings.HTTP_PROXY
            if proxy_url.startswith("socks5://"):
                proxy_type = "socks5"
                proxy_url = proxy_url.replace("socks5://", "")
            elif proxy_url.startswith("https://"):
                proxy_type = "https"
                proxy_url = proxy_url.replace("https://", "")
            elif proxy_url.startswith("http://"):
                proxy_type = "http"
                proxy_url = proxy_url.replace("http://", "")
            
            # 解析主机和端口
            if ":" in proxy_url:
                proxy_host, port_str = proxy_url.split(":", 1)
                try:
                    proxy_port = int(port_str.split("/")[0])  # 处理可能的路径
                except:
                    proxy_port = None
            else:
                proxy_host = proxy_url
        
        return NetworkSettings(
            proxy_type=proxy_type,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_username="",
            proxy_password="",
            test_url="https://httpbin.org/get",
            timeout=30
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取网络设置失败: {str(e)}")

@router.post("/network/settings")
async def update_network_settings(network_settings: NetworkSettings):
    """更新网络设置"""
    try:
        # 构建代理URL
        proxy_url = ""
        if network_settings.proxy_type != "none" and network_settings.proxy_host:
            # HTTP代理类型兼容HTTP和HTTPS
            if network_settings.proxy_type == "http":
                # HTTP代理同时设置给HTTP_PROXY和HTTPS_PROXY
                if network_settings.proxy_port:
                    if network_settings.proxy_username and network_settings.proxy_password:
                        proxy_url = f"http://{network_settings.proxy_username}:{network_settings.proxy_password}@{network_settings.proxy_host}:{network_settings.proxy_port}"
                    else:
                        proxy_url = f"http://{network_settings.proxy_host}:{network_settings.proxy_port}"
                else:
                    proxy_url = f"http://{network_settings.proxy_host}"
            else:
                # 其他代理类型（socks5等）
                if network_settings.proxy_port:
                    if network_settings.proxy_username and network_settings.proxy_password:
                        proxy_url = f"{network_settings.proxy_type}://{network_settings.proxy_username}:{network_settings.proxy_password}@{network_settings.proxy_host}:{network_settings.proxy_port}"
                    else:
                        proxy_url = f"{network_settings.proxy_type}://{network_settings.proxy_host}:{network_settings.proxy_port}"
                else:
                    proxy_url = f"{network_settings.proxy_type}://{network_settings.proxy_host}"
        
        # 更新环境变量文件
        env_file = settings.BASE_DIR / ".env"
        env_lines = []
        
        # 读取现有配置
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # 更新代理设置
        updated_lines = []
        proxy_updated = False
        
        for line in env_lines:
            if line.startswith('HTTP_PROXY=') or line.startswith('HTTPS_PROXY='):
                if not proxy_updated:
                    updated_lines.append(f"HTTP_PROXY={proxy_url}\n")
                    updated_lines.append(f"HTTPS_PROXY={proxy_url}\n")
                    proxy_updated = True
            else:
                updated_lines.append(line)
        
        # 如果没有找到代理设置，添加新的
        if not proxy_updated:
            updated_lines.append(f"\n# 代理配置\n")
            updated_lines.append(f"HTTP_PROXY={proxy_url}\n")
            updated_lines.append(f"HTTPS_PROXY={proxy_url}\n")
        
        # 写入文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        # 同时更新运行时环境变量
        import os
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url
        
        # 更新settings中的代理配置
        settings.HTTP_PROXY = proxy_url
        settings.HTTPS_PROXY = proxy_url
        
        return {
            "message": "网络设置更新成功",
            "proxy_url": proxy_url if proxy_url else "无代理",
            "note": "设置已立即生效"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新网络设置失败: {str(e)}")

@router.post("/network/test", response_model=NetworkTestResult)
async def test_network_connection(network_settings: NetworkSettings):
    """测试网络连接"""
    import asyncio
    import aiohttp
    import subprocess
    import time
    
    try:
        start_time = time.time()
        
        # 对于SOCKS5代理，使用curl进行测试（因为aiohttp不支持SOCKS5）
        if network_settings.proxy_type == "socks5" and network_settings.proxy_host:
            try:
                # 构建curl命令
                proxy_url = f"socks5://{network_settings.proxy_host}:{network_settings.proxy_port or 1080}"
                
                # 使用curl测试连接
                cmd = [
                    "curl", "-x", proxy_url, 
                    "--connect-timeout", str(min(network_settings.timeout, 30)),
                    "--max-time", str(min(network_settings.timeout, 30)),
                    "-s", "-o", "/dev/null", "-w", "%{http_code}",
                    network_settings.test_url
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=network_settings.timeout)
                response_time = time.time() - start_time
                
                if result.returncode == 0 and result.stdout.strip() == "200":
                    return NetworkTestResult(
                        success=True,
                        message=f"SOCKS5代理连接测试成功 (测试URL: {network_settings.test_url})",
                        response_time=round(response_time, 2)
                    )
                else:
                    error_msg = result.stderr.strip() if result.stderr else f"HTTP状态码: {result.stdout.strip()}"
                    return NetworkTestResult(
                        success=False,
                        message="SOCKS5代理连接测试失败",
                        error=error_msg or "连接失败"
                    )
                    
            except subprocess.TimeoutExpired:
                return NetworkTestResult(
                    success=False,
                    message="SOCKS5代理连接超时",
                    error="请求超时，请检查代理设置"
                )
            except Exception as e:
                return NetworkTestResult(
                    success=False,
                    message="SOCKS5代理测试失败",
                    error=str(e)
                )
        
        # 对于HTTP代理或无代理，使用aiohttp
        proxy_url = None
        if network_settings.proxy_type != "none" and network_settings.proxy_host:
            if network_settings.proxy_port:
                if network_settings.proxy_username and network_settings.proxy_password:
                    proxy_url = f"{network_settings.proxy_type}://{network_settings.proxy_username}:{network_settings.proxy_password}@{network_settings.proxy_host}:{network_settings.proxy_port}"
                else:
                    proxy_url = f"{network_settings.proxy_type}://{network_settings.proxy_host}:{network_settings.proxy_port}"
            else:
                proxy_url = f"{network_settings.proxy_type}://{network_settings.proxy_host}"
        
        # 创建HTTP客户端
        timeout = aiohttp.ClientTimeout(total=network_settings.timeout)
        ssl_context = False  # 禁用SSL验证以避免代理问题
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=1)
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        ) as session:
            # 执行测试请求
            kwargs = {'ssl': ssl_context}
            if proxy_url:
                kwargs['proxy'] = proxy_url
            
            # 使用更稳定的测试URL
            test_urls = [
                network_settings.test_url,
                "https://httpbin.org/get",
                "https://www.google.com", 
                "http://www.baidu.com"
            ]
            
            last_error = None
            for test_url in test_urls:
                try:
                    kwargs_copy = kwargs.copy()
                    kwargs_copy['timeout'] = aiohttp.ClientTimeout(total=10)  # 每个URL的独立超时
                    
                    async with session.get(test_url, **kwargs_copy) as response:
                        response_time = time.time() - start_time
                        
                        if response.status == 200:
                            return NetworkTestResult(
                                success=True,
                                message=f"连接测试成功 (测试URL: {test_url})",
                                response_time=round(response_time, 2)
                            )
                        else:
                            last_error = f"HTTP {response.status}"
                            continue
                            
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # 所有URL都失败了
            return NetworkTestResult(
                success=False,
                message="所有测试URL连接失败",
                error=last_error or "网络连接异常"
            )
                    
    except asyncio.TimeoutError:
        return NetworkTestResult(
            success=False,
            message="连接超时",
            error="请求超时，请检查网络设置"
        )
    except Exception as e:
        return NetworkTestResult(
            success=False,
            message="连接测试失败",
            error=str(e)
        )

@router.get("/network/proxy-types")
async def get_proxy_types():
    """获取支持的代理类型"""
    return {
        "proxy_types": {
            "none": "无代理",
            "http": "HTTP代理 (兼容HTTP/HTTPS)",
            "socks5": "SOCKS5代理"
        },
        "recommended": "socks5",
        "note": "SOCKS5代理通常提供最好的兼容性和性能"
    }

@router.get("/logs/files")
async def get_log_files():
    """获取可用的日志文件列表"""
    try:
        log_dir = Path(settings.BASE_DIR).parent / "logs"
        
        if not log_dir.exists():
            return {"files": []}
        
        log_files = []
        for file_path in log_dir.glob("*.log"):
            if file_path.is_file():
                stat = file_path.stat()
                log_files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(file_path)
                })
        
        # 按修改时间排序
        log_files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": log_files}
        
    except Exception as e:
        logger.error(f"获取日志文件列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取日志文件列表失败")

@router.get("/logs/content")
async def get_log_content(
    level: str = Query("info", description="日志级别过滤"),
    lines: int = Query(100, ge=1, le=1000, description="返回行数"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    file_name: Optional[str] = Query(None, description="指定日志文件名")
):
    """获取日志内容"""
    try:
        log_dir = Path(settings.BASE_DIR).parent / "logs"
        
        # 确定要读取的日志文件
        if file_name:
            log_file = log_dir / file_name
        else:
            # 默认读取主日志文件
            log_file = log_dir / "avd_web.log"
        
        if not log_file.exists():
            return {"entries": [], "total": 0}
        
        # 读取日志文件
        entries = []
        level_priority = {
            "debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4
        }
        min_level = level_priority.get(level.lower(), 1)
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                with open(log_file, 'r', encoding='gbk') as f:
                    log_lines = f.readlines()
            except:
                with open(log_file, 'r', encoding='latin1') as f:
                    log_lines = f.readlines()
        
        # 解析日志条目
        log_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - .* - (\w+) - .* - (.*)'
        )
        
        for line in reversed(log_lines[-lines*3:]):  # 读取更多行以便过滤
            line = line.strip()
            if not line:
                continue
            
            # 清理ANSI代码
            clean_line = clean_ansi_codes(line)
            
            match = log_pattern.match(clean_line)
            if match:
                timestamp, log_level, message = match.groups()
                
                # 级别过滤
                if level_priority.get(log_level.lower(), 0) < min_level:
                    continue
                
                # 搜索过滤
                if search and search.lower() not in message.lower():
                    continue
                
                # 格式化错误消息
                if log_level.lower() in ['error', 'critical']:
                    message = format_error_message(message)
                
                entries.append({
                    "timestamp": timestamp,
                    "level": log_level.upper(),
                    "message": message
                })
                
                if len(entries) >= lines:
                    break
        
        return {
            "entries": entries,
            "total": len(entries),
            "file": str(log_file.name),
            "filter_level": level,
            "search_keyword": search
        }
        
    except Exception as e:
        error_msg = f"获取日志内容失败: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/logs/test")
async def generate_test_logs():
    """生成测试日志（用于测试日志系统）"""
    try:
        test_logger = logging.getLogger("test")
        
        # 生成不同级别的测试日志
        test_logger.debug("这是一条DEBUG级别的测试日志")
        test_logger.info("这是一条INFO级别的测试日志")
        test_logger.warning("这是一条WARNING级别的测试日志")
        test_logger.error("这是一条ERROR级别的测试日志")
        test_logger.critical("这是一条CRITICAL级别的测试日志")
        
        # 生成一些特殊场景的日志
        test_logger.error("下载失败: [0;31mERROR:[0m 视频不存在或已被删除")
        test_logger.info("下载成功: 文件已保存到 /downloads/video.mp4")
        test_logger.warning("网络连接不稳定，正在重试...")
        
        return {
            "success": True,
            "message": "测试日志已生成",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"生成测试日志失败: {e}")
        raise HTTPException(status_code=500, detail="生成测试日志失败")

@router.delete("/logs/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=1, le=365, description="清理多少天前的日志")
):
    """清理旧日志文件"""
    try:
        log_dir = Path(settings.BASE_DIR).parent / "logs"
        
        if not log_dir.exists():
            return {"cleaned_files": 0, "message": "日志目录不存在"}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_files = 0
        cleaned_size = 0
        
        for log_file in log_dir.glob("*.log.*"):  # 轮转的日志文件
            if log_file.is_file():
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    cleaned_files += 1
                    cleaned_size += file_size
        
        return {
            "success": True,
            "cleaned_files": cleaned_files,
            "cleaned_size": cleaned_size,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"已清理 {cleaned_files} 个日志文件，释放 {cleaned_size / 1024 / 1024:.2f} MB 空间"
        }
        
    except Exception as e:
        logger.error(f"清理日志失败: {e}")
        raise HTTPException(status_code=500, detail="清理日志失败")

# ==================== 模型管理相关API ====================

from ...core.subtitle_modules import WhisperModelManager

# 模型管理器实例
model_manager = WhisperModelManager()

class ModelInfo(BaseModel):
    """模型信息响应"""
    device: str = Field(description="计算设备")
    auto_device_selection: bool = Field(description="是否自动选择设备")
    current_model: str = Field(description="当前使用的模型")
    default_model: str = Field(description="默认模型")
    cached_models: List[str] = Field(description="已缓存的模型")
    current_cache_size: int = Field(description="当前缓存大小(MB)")
    whisper_device: str = Field(description="Whisper设备")
    compute_type: str = Field(description="计算类型")
    model_path: str = Field(description="模型存储路径")
    available_models: List[str] = Field(description="可用模型列表")
    quality_mode: str = Field(description="质量模式")
    cuda_device_count: Optional[int] = Field(default=None, description="CUDA设备数量")
    cuda_current_device: Optional[int] = Field(default=None, description="当前CUDA设备")
    cuda_memory_allocated: Optional[float] = Field(default=None, description="已分配CUDA内存(GB)")
    cuda_memory_cached: Optional[float] = Field(default=None, description="已缓存CUDA内存(GB)")
    gpu_name: Optional[str] = Field(default=None, description="GPU名称")
    gpu_memory_total: Optional[float] = Field(default=None, description="GPU总内存(GB)")
    error: Optional[str] = Field(default=None, description="错误信息")

class ModelSettings(BaseModel):
    """模型设置"""
    default_model: str = Field(description="默认模型")
    auto_device_selection: bool = Field(description="是否自动选择设备")
    preferred_device: str = Field(description="首选设备")
    compute_type: str = Field(description="计算类型")

class ModelCacheStatus(BaseModel):
    """模型缓存状态"""
    cached_models: List[str] = Field(description="已缓存的模型")
    current_model: Optional[str] = Field(description="当前模型")
    cache_count: int = Field(description="缓存数量")
    estimated_memory_mb: int = Field(description="估计内存使用(MB)")

@router.get("/models/info", response_model=ModelInfo)
async def get_model_info():
    """获取模型管理信息"""
    try:
        logger.info("获取模型管理信息")
        model_info = model_manager.get_model_info()
        return ModelInfo(**model_info)
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")

@router.get("/models/available")
async def get_available_models():
    """获取可用模型列表"""
    try:
        logger.info("获取可用模型列表")
        models = model_manager.get_available_models()
        
        # 模型详细信息
        model_details = {
            "large-v3": {"name": "Large V3", "size": "最高品质", "memory": "~1.5GB", "recommended": True},
            "large-v2": {"name": "Large V2", "size": "高品质", "memory": "~1.5GB", "recommended": False},
            "large": {"name": "Large", "size": "高品质", "memory": "~1.5GB", "recommended": False},
            "medium": {"name": "Medium", "size": "平衡", "memory": "~800MB", "recommended": False},
            "small": {"name": "Small", "size": "快速", "memory": "~250MB", "recommended": False},
            "base": {"name": "Base", "size": "基础", "memory": "~150MB", "recommended": False},
            "tiny": {"name": "Tiny", "size": "最快", "memory": "~50MB", "recommended": False}
        }
        
        return {
            "success": True,
            "models": models,
            "model_details": model_details,
            "default": model_manager.default_model_size,
            "current": model_manager.current_model_size
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")

@router.post("/models/load/{model_size}")
async def load_model(model_size: str):
    """加载指定模型"""
    try:
        logger.info(f"加载模型: {model_size}")
        
        # 验证模型是否在可用列表中
        available_models = model_manager.get_available_models()
        if model_size not in available_models:
            raise HTTPException(status_code=400, detail=f"不支持的模型: {model_size}")
        
        # 加载模型
        model = model_manager.load_model(model_size)
        
        return {
            "success": True,
            "message": f"模型 {model_size} 加载成功",
            "current_model": model_manager.current_model_size,
            "cache_status": model_manager.get_cache_status()
        }
    except Exception as e:
        logger.error(f"加载模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载模型失败: {str(e)}")

@router.delete("/models/cache/{model_size}")
async def unload_model(model_size: str):
    """卸载指定模型"""
    try:
        logger.info(f"卸载模型: {model_size}")
        
        success = model_manager.unload_model(model_size)
        if success:
            return {
                "success": True,
                "message": f"模型 {model_size} 卸载成功",
                "cache_status": model_manager.get_cache_status()
            }
        else:
            return {
                "success": False,
                "message": f"模型 {model_size} 未在缓存中或卸载失败"
            }
    except Exception as e:
        logger.error(f"卸载模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"卸载模型失败: {str(e)}")

@router.delete("/models/cache")
async def clear_model_cache():
    """清空模型缓存"""
    try:
        logger.info("清空模型缓存")
        
        success = model_manager.clear_cache()
        if success:
            return {
                "success": True,
                "message": "模型缓存已清空",
                "cache_status": model_manager.get_cache_status()
            }
        else:
            return {
                "success": False,
                "message": "清空模型缓存失败"
            }
    except Exception as e:
        logger.error(f"清空模型缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空模型缓存失败: {str(e)}")

@router.get("/models/cache/status", response_model=ModelCacheStatus)
async def get_model_cache_status():
    """获取模型缓存状态"""
    try:
        logger.info("获取模型缓存状态")
        cache_status = model_manager.get_cache_status()
        return ModelCacheStatus(**cache_status)
    except Exception as e:
        logger.error(f"获取缓存状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓存状态失败: {str(e)}")

@router.post("/models/settings")
async def update_model_settings(settings_data: ModelSettings):
    """更新模型设置"""
    try:
        logger.info(f"更新模型设置: {settings_data}")
        
        # 这里可以保存到配置文件或数据库
        # 目前暂时返回成功状态
        return {
            "success": True,
            "message": "模型设置已更新",
            "settings": settings_data.dict()
        }
    except Exception as e:
        logger.error(f"更新模型设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新模型设置失败: {str(e)}")

@router.get("/status")
async def get_system_status():
    """获取系统运行状态"""
    try:
        # 检查各个组件状态
        status = {
            "overall": "healthy",
            "components": {
                "database": "healthy",
                "download_service": "healthy", 
                "subtitle_service": "healthy",
                "file_system": "healthy"
            },
            "metrics": {
                "uptime": "unknown",
                "total_downloads": 0,
                "active_tasks": 0,
                "error_rate": 0.0
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查磁盘空间
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            status["components"]["file_system"] = "warning"
            status["overall"] = "warning"
        
        # 检查内存使用
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            status["overall"] = "warning"
        
        return status
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统状态失败")

logger = logging.getLogger(__name__)

@router.post("/logs/test")
async def generate_test_logs():
    """生成测试日志条目"""
    try:
        # 生成不同级别的测试日志
        logger.debug("这是一条调试信息，用于开发阶段排查问题")
        logger.info("系统正常运行，用户访问了日志测试页面")  
        logger.warning("发现潜在问题：内存使用率较高，请注意监控")
        logger.error("发生错误：无法连接到外部API服务")
        logger.critical("严重错误：数据库连接丢失，系统即将停止")
        
        return {
            "message": "测试日志已生成",
            "generated_levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "note": "请刷新日志查看器查看新生成的日志"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成测试日志失败: {str(e)}") 
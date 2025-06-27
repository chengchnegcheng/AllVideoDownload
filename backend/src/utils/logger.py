"""
AVD Web版本 - 日志配置模块

提供统一的日志配置和管理
"""

import logging
import logging.config
import os
import re
from pathlib import Path
from typing import Optional


def clean_ansi_codes(text: str) -> str:
    """清理文本中的ANSI颜色代码和控制字符
    
    Args:
        text: 包含ANSI代码的文本
        
    Returns:
        清理后的纯文本
    """
    # ANSI颜色代码和控制字符的正则表达式
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    # 清理ANSI代码
    cleaned = ansi_escape.sub('', text)
    
    # 清理其他常见的控制字符
    cleaned = re.sub(r'\[\d+;\d+m', '', cleaned)  # 颜色代码 [31;1m
    cleaned = re.sub(r'\[\d+m', '', cleaned)      # 简单颜色代码 [31m
    cleaned = re.sub(r'\[0m', '', cleaned)        # 重置代码 [0m
    
    return cleaned.strip()


def format_error_message(error_msg: str, context: str = "") -> str:
    """格式化错误消息，使其更易读
    
    Args:
        error_msg: 原始错误消息
        context: 错误上下文信息
        
    Returns:
        格式化后的错误消息
    """
    # 清理ANSI代码
    cleaned_msg = clean_ansi_codes(str(error_msg))
    
    # 提取主要错误信息
    if "ERROR:" in cleaned_msg:
        # 提取ERROR:后的主要信息
        parts = cleaned_msg.split("ERROR:")
        if len(parts) > 1:
            main_error = parts[1].split(";")[0].strip()
            # 进一步清理
            main_error = re.sub(r'\s+', ' ', main_error)  # 合并多余空格
            main_error = main_error.replace("please report this issue on", "")
            main_error = main_error.split("Confirm you are on the latest version")[0].strip()
            
            if context:
                return f"{context}: {main_error}"
            return main_error
    
    # 如果没有特殊格式，直接返回清理后的消息
    cleaned_msg = re.sub(r'\s+', ' ', cleaned_msg)  # 合并多余空格
    if context and not cleaned_msg.startswith(context):
        return f"{context}: {cleaned_msg}"
    return cleaned_msg


def setup_logger(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    app_name: str = "avd_web"
) -> None:
    """设置应用日志配置
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录，默认为项目根目录下的logs
        app_name: 应用名称，用于日志文件命名
    """
    # 确定日志目录
    if log_dir is None:
        # 项目根目录的logs文件夹
        project_root = Path(__file__).parent.parent.parent.parent
        log_dir = project_root / "logs"
    else:
        log_dir = Path(log_dir)
    
    # 创建日志目录
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志文件路径
    log_file = log_dir / f"{app_name}.log"
    error_log_file = log_dir / f"{app_name}_error.log"
    
    # 日志配置
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "console",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(log_file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(error_log_file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "": {  # 根日志器
                "level": log_level.upper(),
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["file"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            },
            "yt_dlp": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            }
        }
    }
    
    # 应用日志配置
    logging.config.dictConfig(logging_config)
    
    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成，日志文件: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        日志器实例
    """
    return logging.getLogger(name)


class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self, logger_name: str = "request"):
        self.logger = get_logger(logger_name)
    
    def log_request(self, method: str, url: str, client_ip: str, user_agent: str = ""):
        """记录请求信息"""
        self.logger.info(f"请求: {method} {url} - IP: {client_ip} - UA: {user_agent}")
    
    def log_response(self, method: str, url: str, status_code: int, response_time: float):
        """记录响应信息"""
        self.logger.info(f"响应: {method} {url} - 状态码: {status_code} - 耗时: {response_time:.3f}s")
    
    def log_error(self, method: str, url: str, error: Exception):
        """记录错误信息"""
        self.logger.error(f"错误: {method} {url} - {type(error).__name__}: {str(error)}")


class DownloadLogger:
    """下载日志记录器"""
    
    def __init__(self, logger_name: str = "download"):
        self.logger = get_logger(logger_name)
    
    def log_start(self, task_id: str, url: str, options: dict):
        """记录下载开始"""
        self.logger.info(f"开始下载: {task_id} - URL: {url} - 选项: {options}")
    
    def log_progress(self, task_id: str, progress: float, speed: float = 0):
        """记录下载进度"""
        self.logger.debug(f"下载进度: {task_id} - {progress:.1f}% - 速度: {speed:.1f}KB/s")
    
    def log_complete(self, task_id: str, file_path: str, file_size: int = 0):
        """记录下载完成"""
        self.logger.info(f"下载完成: {task_id} - 文件: {file_path} - 大小: {file_size}字节")
    
    def log_error(self, task_id: str, error: Exception):
        """记录下载错误"""
        self.logger.error(f"下载失败: {task_id} - {type(error).__name__}: {str(error)}")
    
    def log_cancel(self, task_id: str):
        """记录下载取消"""
        self.logger.info(f"下载取消: {task_id}")


class SubtitleLogger:
    """字幕日志记录器"""
    
    def __init__(self, logger_name: str = "subtitle"):
        self.logger = get_logger(logger_name)
    
    def log_generation_start(self, task_id: str, audio_file: str, language: str):
        """记录字幕生成开始"""
        self.logger.info(f"开始生成字幕: {task_id} - 音频: {audio_file} - 语言: {language}")
    
    def log_generation_complete(self, task_id: str, subtitle_file: str):
        """记录字幕生成完成"""
        self.logger.info(f"字幕生成完成: {task_id} - 文件: {subtitle_file}")
    
    def log_translation_start(self, task_id: str, source_lang: str, target_lang: str):
        """记录字幕翻译开始"""
        self.logger.info(f"开始翻译字幕: {task_id} - {source_lang} -> {target_lang}")
    
    def log_translation_complete(self, task_id: str, translated_file: str):
        """记录字幕翻译完成"""
        self.logger.info(f"字幕翻译完成: {task_id} - 文件: {translated_file}")
    
    def log_error(self, task_id: str, operation: str, error: Exception):
        """记录字幕操作错误"""
        self.logger.error(f"字幕{operation}失败: {task_id} - {type(error).__name__}: {str(error)}")


# 全局日志记录器实例
request_logger = RequestLogger()
download_logger = DownloadLogger()
subtitle_logger = SubtitleLogger() 
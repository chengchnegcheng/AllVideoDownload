"""
统一的临时文件管理器

提供临时文件的创建、跟踪和自动清理功能
"""

import asyncio
import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..core.config import settings

logger = logging.getLogger(__name__)


class TempFileManager:
    """临时文件管理器 - 单例模式"""

    _instance: Optional["TempFileManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "TempFileManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._temp_files: Set[str] = set()
        self._file_metadata: Dict[str, Dict[str, Any]] = {}
        self._cleanup_tasks: Set[asyncio.Task] = set()
        self._initialized = True

        # 确保临时目录存在
        os.makedirs(settings.TEMP_PATH, exist_ok=True)

        logger.info("临时文件管理器初始化完成")

    def create_temp_file(
        self,
        suffix: str = "",
        prefix: str = "avd_",
        directory: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> str:
        """
        创建临时文件

        Args:
            suffix: 文件后缀
            prefix: 文件前缀
            directory: 指定目录，默认使用系统临时目录
            content: 文件内容

        Returns:
            临时文件路径
        """
        try:
            if directory is None:
                directory = settings.TEMP_PATH

            # 确保目录存在
            os.makedirs(directory, exist_ok=True)

            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(
                suffix=suffix, prefix=prefix, dir=directory
            )

            try:
                if content is not None:
                    os.write(fd, content)
            finally:
                os.close(fd)

            # 注册到管理器
            self._register_temp_file(temp_path)

            logger.debug(f"创建临时文件: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"创建临时文件失败: {e}")
            raise

    def create_temp_dir(
        self, prefix: str = "avd_", directory: Optional[str] = None
    ) -> str:
        """
        创建临时目录

        Args:
            prefix: 目录前缀
            directory: 父目录

        Returns:
            临时目录路径
        """
        try:
            if directory is None:
                directory = settings.TEMP_PATH

            # 确保父目录存在
            os.makedirs(directory, exist_ok=True)

            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix=prefix, dir=directory)

            # 注册到管理器
            self._register_temp_file(temp_dir)

            logger.debug(f"创建临时目录: {temp_dir}")
            return temp_dir

        except Exception as e:
            logger.error(f"创建临时目录失败: {e}")
            raise

    def _register_temp_file(self, file_path: str):
        """注册临时文件"""
        self._temp_files.add(file_path)
        self._file_metadata[file_path] = {
            "created_at": datetime.now(),
            "size": 0,
            "type": "directory" if os.path.isdir(file_path) else "file",
        }

        # 更新文件大小
        try:
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    self._file_metadata[file_path]["size"] = os.path.getsize(file_path)
                elif os.path.isdir(file_path):
                    total_size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(file_path)
                        for filename in filenames
                    )
                    self._file_metadata[file_path]["size"] = total_size
        except Exception as e:
            logger.warning(f"获取文件大小失败: {e}")

    def register_existing_file(self, file_path: str):
        """注册已存在的文件为临时文件"""
        if os.path.exists(file_path):
            self._register_temp_file(file_path)
            logger.debug(f"注册现有文件为临时文件: {file_path}")

    def cleanup_file(self, file_path: str) -> bool:
        """
        清理单个临时文件

        Args:
            file_path: 文件路径

        Returns:
            是否清理成功
        """
        try:
            if file_path in self._temp_files:
                if os.path.exists(file_path):
                    if os.path.isdir(file_path):
                        import shutil

                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)

                self._temp_files.discard(file_path)
                self._file_metadata.pop(file_path, None)

                logger.debug(f"清理临时文件: {file_path}")
                return True

        except Exception as e:
            logger.warning(f"清理临时文件失败 {file_path}: {e}")

        return False

    async def cleanup_all(self) -> Dict[str, Any]:
        """
        清理所有临时文件

        Returns:
            清理结果统计
        """
        async with self._lock:
            cleaned_count = 0
            failed_count = 0
            total_size = 0

            temp_files_copy = self._temp_files.copy()

            for file_path in temp_files_copy:
                try:
                    file_size = self._file_metadata.get(file_path, {}).get("size", 0)
                    if self.cleanup_file(file_path):
                        cleaned_count += 1
                        total_size += file_size
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"清理文件失败 {file_path}: {e}")
                    failed_count += 1

            result = {
                "cleaned_count": cleaned_count,
                "failed_count": failed_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "remaining_files": len(self._temp_files),
            }

            logger.info(f"临时文件清理完成: {result}")
            return result

    async def cleanup_expired(self, max_age_hours: float = 1.0) -> Dict[str, Any]:
        """
        清理过期的临时文件

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            清理结果统计
        """
        async with self._lock:
            cleaned_count = 0
            total_size = 0
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            expired_files = []
            for file_path in self._temp_files.copy():
                metadata = self._file_metadata.get(file_path, {})
                created_at = metadata.get("created_at")

                if created_at and created_at < cutoff_time:
                    expired_files.append(file_path)

            for file_path in expired_files:
                try:
                    file_size = self._file_metadata.get(file_path, {}).get("size", 0)
                    if self.cleanup_file(file_path):
                        cleaned_count += 1
                        total_size += file_size

                except Exception as e:
                    logger.error(f"清理过期文件失败 {file_path}: {e}")

            result = {
                "cleaned_count": cleaned_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "max_age_hours": max_age_hours,
            }

            logger.info(f"过期临时文件清理完成: {result}")
            return result

    def get_stats(self) -> Dict[str, Any]:
        """获取临时文件统计信息"""
        total_size = sum(
            metadata.get("size", 0) for metadata in self._file_metadata.values()
        )

        file_count = sum(
            1
            for metadata in self._file_metadata.values()
            if metadata.get("type") == "file"
        )

        dir_count = sum(
            1
            for metadata in self._file_metadata.values()
            if metadata.get("type") == "directory"
        )

        return {
            "total_files": len(self._temp_files),
            "file_count": file_count,
            "directory_count": dir_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "temp_directory": settings.TEMP_PATH,
        }

    @asynccontextmanager
    async def temp_file_context(self, **kwargs):
        """
        临时文件上下文管理器

        Args:
            **kwargs: create_temp_file的参数

        Yields:
            临时文件路径
        """
        temp_file = None
        try:
            temp_file = self.create_temp_file(**kwargs)
            yield temp_file
        finally:
            if temp_file:
                self.cleanup_file(temp_file)

    @contextmanager
    def temp_file_sync_context(self, **kwargs):
        """
        同步临时文件上下文管理器

        Args:
            **kwargs: create_temp_file的参数

        Yields:
            临时文件路径
        """
        temp_file = None
        try:
            temp_file = self.create_temp_file(**kwargs)
            yield temp_file
        finally:
            if temp_file:
                self.cleanup_file(temp_file)


# 全局临时文件管理器实例
temp_file_manager = TempFileManager()


# 便捷函数
def create_temp_file(
    suffix: str = "",
    prefix: str = "avd_",
    directory: Optional[str] = None,
    content: Optional[bytes] = None,
) -> str:
    """创建临时文件的便捷函数"""
    return temp_file_manager.create_temp_file(suffix, prefix, directory, content)


def create_temp_dir(prefix: str = "avd_", directory: Optional[str] = None) -> str:
    """创建临时目录的便捷函数"""
    return temp_file_manager.create_temp_dir(prefix, directory)


def cleanup_temp_file(file_path: str) -> bool:
    """清理临时文件的便捷函数"""
    return temp_file_manager.cleanup_file(file_path)


async def cleanup_all_temp_files() -> Dict[str, Any]:
    """清理所有临时文件的便捷函数"""
    return await temp_file_manager.cleanup_all()


async def cleanup_expired_temp_files(max_age_hours: float = 1.0) -> Dict[str, Any]:
    """清理过期临时文件的便捷函数"""
    return await temp_file_manager.cleanup_expired(max_age_hours)

"""
通用装饰器集合

提供异常处理、重试、性能监控等通用装饰器
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def handle_api_errors(
    default_status_code: int = 500,
    error_message_prefix: str = "",
    log_errors: bool = True,
    reraise_http_exceptions: bool = True,
):
    """
    API错误处理装饰器

    Args:
        default_status_code: 默认HTTP状态码
        error_message_prefix: 错误消息前缀
        log_errors: 是否记录错误日志
        reraise_http_exceptions: 是否重新抛出HTTPException
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                if reraise_http_exceptions:
                    raise
                # 如果不重新抛出，则转换为通用错误
                if log_errors:
                    logger.error(f"{error_message_prefix}HTTP异常: {func.__name__}")
                raise HTTPException(
                    status_code=default_status_code,
                    detail=f"{error_message_prefix}操作失败",
                )
            except Exception as e:
                error_msg = (
                    f"{error_message_prefix}{str(e)}"
                    if error_message_prefix
                    else str(e)
                )

                if log_errors:
                    logger.error(f"{func.__name__}执行失败: {e}", exc_info=True)

                raise HTTPException(status_code=default_status_code, detail=error_msg)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                if reraise_http_exceptions:
                    raise
                if log_errors:
                    logger.error(f"{error_message_prefix}HTTP异常: {func.__name__}")
                raise HTTPException(
                    status_code=default_status_code,
                    detail=f"{error_message_prefix}操作失败",
                )
            except Exception as e:
                error_msg = (
                    f"{error_message_prefix}{str(e)}"
                    if error_message_prefix
                    else str(e)
                )

                if log_errors:
                    logger.error(f"{func.__name__}执行失败: {e}", exc_info=True)

                raise HTTPException(status_code=default_status_code, detail=error_msg)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间(秒)
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # 最后一次尝试失败
                        logger.error(f"{func.__name__}重试{max_attempts}次后仍失败: {e}")
                        raise

                    # 记录重试信息
                    logger.warning(
                        f"{func.__name__}第{attempt + 1}次尝试失败，"
                        f"{current_delay:.1f}秒后重试: {e}"
                    )

                    # 调用重试回调
                    if on_retry:
                        try:
                            if asyncio.iscoroutinefunction(on_retry):
                                await on_retry(attempt + 1, e)
                            else:
                                on_retry(attempt + 1, e)
                        except Exception as callback_error:
                            logger.warning(f"重试回调执行失败: {callback_error}")

                    # 等待后重试
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor

            # 理论上不会到达这里
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(f"{func.__name__}重试{max_attempts}次后仍失败: {e}")
                        raise

                    logger.warning(
                        f"{func.__name__}第{attempt + 1}次尝试失败，"
                        f"{current_delay:.1f}秒后重试: {e}"
                    )

                    if on_retry:
                        try:
                            on_retry(attempt + 1, e)
                        except Exception as callback_error:
                            logger.warning(f"重试回调执行失败: {callback_error}")

                    time.sleep(current_delay)
                    current_delay *= backoff_factor

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def log_execution_time(
    log_level: int = logging.INFO,
    message_template: str = "{func_name}执行完成，耗时: {duration:.2f}秒",
):
    """
    记录执行时间装饰器

    Args:
        log_level: 日志级别
        message_template: 消息模板
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log(
                    log_level,
                    message_template.format(func_name=func.__name__, duration=duration),
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func.__name__}执行失败，耗时: {duration:.2f}秒，错误: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log(
                    log_level,
                    message_template.format(func_name=func.__name__, duration=duration),
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func.__name__}执行失败，耗时: {duration:.2f}秒，错误: {e}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def validate_input(validation_func: Callable):
    """
    输入验证装饰器

    Args:
        validation_func: 验证函数，应该抛出异常如果验证失败
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # 执行验证
            if asyncio.iscoroutinefunction(validation_func):
                await validation_func(*args, **kwargs)
            else:
                validation_func(*args, **kwargs)

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            validation_func(*args, **kwargs)
            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def cache_result(
    ttl_seconds: int = 300, max_size: int = 128, key_func: Optional[Callable] = None
):
    """
    结果缓存装饰器（简单实现）

    Args:
        ttl_seconds: 缓存存活时间
        max_size: 最大缓存大小
        key_func: 自定义key生成函数
    """

    def decorator(func: Callable) -> Callable:
        cache: Dict[str, Dict[str, Any]] = {}

        def generate_key(*args, **kwargs) -> str:
            if key_func:
                return key_func(*args, **kwargs)
            return str(hash((args, tuple(sorted(kwargs.items())))))

        def is_expired(timestamp: float) -> bool:
            return time.time() - timestamp > ttl_seconds

        def cleanup_cache():
            """清理过期缓存"""
            current_time = time.time()
            expired_keys = [
                key
                for key, data in cache.items()
                if current_time - data["timestamp"] > ttl_seconds
            ]
            for key in expired_keys:
                del cache[key]

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # 清理过期缓存
            if len(cache) > max_size // 2:
                cleanup_cache()

            # 生成缓存key
            cache_key = generate_key(*args, **kwargs)

            # 检查缓存
            if cache_key in cache:
                cached_data = cache[cache_key]
                if not is_expired(cached_data["timestamp"]):
                    logger.debug(f"{func.__name__}使用缓存结果")
                    return cached_data["result"]
                else:
                    del cache[cache_key]

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)

            # 检查缓存大小限制
            if len(cache) >= max_size:
                # 删除最旧的缓存项
                oldest_key = min(cache.keys(), key=lambda k: cache[k]["timestamp"])
                del cache[oldest_key]

            cache[cache_key] = {"result": result, "timestamp": time.time()}

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if len(cache) > max_size // 2:
                cleanup_cache()

            cache_key = generate_key(*args, **kwargs)

            if cache_key in cache:
                cached_data = cache[cache_key]
                if not is_expired(cached_data["timestamp"]):
                    logger.debug(f"{func.__name__}使用缓存结果")
                    return cached_data["result"]
                else:
                    del cache[cache_key]

            result = func(*args, **kwargs)

            if len(cache) >= max_size:
                oldest_key = min(cache.keys(), key=lambda k: cache[k]["timestamp"])
                del cache[oldest_key]

            cache[cache_key] = {"result": result, "timestamp": time.time()}

            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# 预设的装饰器组合
def api_endpoint(error_prefix: str = "", max_retries: int = 0, log_time: bool = False):
    """
    API端点装饰器组合

    Args:
        error_prefix: 错误消息前缀
        max_retries: 最大重试次数
        log_time: 是否记录执行时间
    """

    def decorator(func: Callable) -> Callable:
        # 应用装饰器（顺序很重要）
        decorated_func = func

        # 1. 错误处理（最外层）
        decorated_func = handle_api_errors(
            error_message_prefix=error_prefix,
            log_errors=True,
            reraise_http_exceptions=True,
        )(decorated_func)

        # 2. 重试（如果需要）
        if max_retries > 0:
            decorated_func = retry(
                max_attempts=max_retries + 1, delay=1.0, backoff_factor=1.5
            )(decorated_func)

        # 3. 性能监控（如果需要）
        if log_time:
            decorated_func = log_execution_time()(decorated_func)

        return decorated_func

    return decorator


def download_endpoint(max_retries: int = 2):
    """下载端点专用装饰器"""
    return api_endpoint(error_prefix="下载失败: ", max_retries=max_retries, log_time=True)


def subtitle_endpoint(max_retries: int = 1):
    """字幕端点专用装饰器"""
    return api_endpoint(error_prefix="字幕处理失败: ", max_retries=max_retries, log_time=True)

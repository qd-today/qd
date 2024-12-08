import asyncio
import inspect
import logging
import threading
from functools import wraps
from typing import Any, Optional

import umsgpack  # type: ignore
from cachetools import FIFOCache, LRUCache, RRCache, TLRUCache, TTLCache

from qd_core.config import get_settings
from qd_core.utils.i18n import gettext
from qd_core.utils.log import Log

logger_decorator = Log("QD.Core.Utils").getlogger()


def log_and_raise_error(
    logger: logging.Logger, error_message_format: str, raise_exception: bool = True, log_level=logging.ERROR
):
    """
    创建一个装饰器，用于在函数执行时记录错误信息，并根据配置决定是否抛出异常。

    Args:
        logger (logging.Logger): 用于记录日志的logger实例。
        error_message_format (str): 错误信息的格式字符串，应包含将异常信息插入的位置。
        raise_exception (bool): 是否在函数执行时抛出异常。默认为 True。
        log_level (int): 记录错误信息的日志级别。默认为 logging.ERROR。

    Returns:
        decorator: 该装饰器将给定的函数包装在一个处理异常并记录日志的函数中。
    """

    def decorator(func):
        # 检查被装饰的函数是否为异步函数，并根据结果定义不同的包装器
        if inspect.iscoroutinefunction(func):
            # 为异步函数定义的包装器
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # 记录异常信息，并根据配置决定是否抛出
                    logger.log(log_level, error_message_format, str(e), exc_info=get_settings().log.traceback_print)
                    if raise_exception:
                        raise
                    return None
        else:
            # 为同步函数定义的包装器
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # 记录异常信息，并根据配置决定是否抛出
                    logger.log(log_level, error_message_format, str(e), exc_info=get_settings().log.traceback_print)
                    if raise_exception:
                        raise
                    return None

        return wrapper

    return decorator


# 定义一个全局线程局部存储对象
_cache_lock = threading.local()


class FunctionCache:
    def __init__(self, maxsize: int = 1000, cache_type: str = "LRU", ttl: Optional[float] = None, ttu: Any = None):
        self.maxsize = maxsize
        self.cache_type = cache_type
        self.ttl = ttl
        self.ttu = ttu
        self._cache = self._create_cache()

    def _create_cache(
        self,
    ):
        if self.cache_type == "LRU":
            return LRUCache(maxsize=self.maxsize)
        elif self.cache_type == "RR":
            return RRCache(maxsize=self.maxsize)
        elif self.cache_type == "FIFO":
            return FIFOCache(maxsize=self.maxsize)
        elif self.cache_type == "TTL":
            return TTLCache(maxsize=self.maxsize, ttl=self.ttl)
        elif self.cache_type == "TLRU":
            return TLRUCache(maxsize=self.maxsize, ttu=self.ttu)
        else:
            raise ValueError(gettext("Unsupported cache type"))

    def build_key(self, args, kwargs):
        """构建缓存键"""
        tmp = {k: v for k, v in kwargs.items()}
        return umsgpack.packb((args, tmp))

    def get_lock(self):
        """获取锁"""
        lock = getattr(_cache_lock, "lock", None)
        if lock is None:
            if inspect.iscoroutinefunction(self._cache.get):
                lock = asyncio.Lock()
            else:
                lock = threading.Lock()
            setattr(_cache_lock, "lock", lock)
        return lock

    def get_or_create_cache(self, self_instance: Optional["FunctionCache"] = None):
        """获取或创建缓存"""
        return self._cache

    @log_and_raise_error(logger_decorator, gettext("Caching Function Result Error: %s"), log_level=logging.WARNING)
    def _wrapper(self, fn, *args, **kwargs):
        # 检查 kwargs 中是否有 sql_session
        if "sql_session" in kwargs and kwargs["sql_session"] is not None:
            return fn(*args, **kwargs)

        key = self.build_key(args, kwargs)

        lock = self.get_lock()
        if inspect.iscoroutinefunction(fn):

            async def async_wrapper():
                if key in self._cache:
                    return self._cache[key]
                with lock:
                    if key in self._cache:  # 再次检查，防止并发情况下的重复计算
                        return self._cache[key]
                    result = await fn(*args, **kwargs)
                    self._cache[key] = result
                    return self._cache.get(key)

            return async_wrapper()
        else:
            if key in self._cache:
                return self._cache[key]
            with lock:
                if key in self._cache:  # 再次检查，防止并发情况下的重复计算
                    return self._cache[key]
                result = fn(*args, **kwargs)
                self._cache[key] = result
                return self._cache.get(key)

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return self._wrapper(fn, *args, **kwargs)

        return wrapper


class MethodCache(FunctionCache):
    @classmethod
    def get_self_and_args(cls, args):
        return args[0], args[1:]

    def get_or_create_cache(self, self_instance: Optional["FunctionCache"] = None):
        """获取或创建缓存"""
        if self_instance:
            if not hasattr(self_instance, "_cache"):
                self_instance._cache = self._create_cache()
            return self_instance._cache
        return super().get_or_create_cache(self_instance)  # 使用 super() 调用基类方法

    @log_and_raise_error(logger_decorator, gettext("Caching Class Method Result Error: %s"), log_level=logging.WARNING)
    def _wrapper(self, fn, *args, **kwargs):
        # 检查 kwargs 中是否有 sql_session
        if "sql_session" in kwargs and kwargs["sql_session"] is not None:
            return fn(*args, **kwargs)

        self_instance, args = self.get_self_and_args(args)
        cache = self.get_or_create_cache(self_instance)
        key = self.build_key(args, kwargs)

        lock = self.get_lock()
        if inspect.iscoroutinefunction(fn):

            async def async_wrapper():
                if key in cache:
                    return cache[key]
                with lock:
                    if key in cache:  # 再次检查，防止并发情况下的重复计算
                        return cache[key]
                    result = await fn(self_instance, *args, **kwargs)
                    cache[key] = result
                    return cache.get(key)

            return async_wrapper()
        else:
            if key in cache:
                return cache[key]
            with lock:
                if key in cache:  # 再次检查，防止并发情况下的重复计算
                    return cache[key]
                result = fn(self_instance, *args, **kwargs)
                cache[key] = result
                return cache.get(key)

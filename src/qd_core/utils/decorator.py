import functools
import inspect
import logging

import umsgpack  # type: ignore

from qd_core.config import get_settings


def log_and_raise_error(
    logger: logging.Logger, error_message_format: str, raise_exception: bool = True, log_level=logging.ERROR
):
    """
    创建一个装饰器，用于在函数执行时记录错误信息，并根据配置决定是否抛出异常。

    参数:
    logger: logging.Logger - 用于记录日志的logger实例。
    error_message_format: str - 错误信息的格式字符串，应包含将异常信息插入的位置。

    返回:
    返回一个装饰器，该装饰器将给定的函数包装在一个处理异常并记录日志的函数中。
    """

    def decorator(func):
        # 检查被装饰的函数是否为异步函数，并根据结果定义不同的包装器
        if inspect.iscoroutinefunction(func):
            # 为异步函数定义的包装器
            @functools.wraps(func)
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
            @functools.wraps(func)
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


def func_cache(f):
    _cache = {}

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        key = umsgpack.packb((args, kwargs))
        if key not in _cache:
            _cache[key] = f(*args, **kwargs)
        return _cache[key]

    return wrapper


def method_cache(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        # pylint: disable=protected-access
        tmp = {}
        for k, v in kwargs.items():
            if k == "sql_session":
                continue
            tmp[k] = v
        if not hasattr(self, "_cache"):
            self._cache = {}
        key = umsgpack.packb((args, tmp))
        if key not in self._cache:
            self._cache[key] = fn(self, *args, **kwargs)
        return self._cache[key]

    return wrapper

import functools
import inspect
import logging
from functools import wraps
from typing import Any, Callable

import umsgpack  # type: ignore
from pydantic import TypeAdapter

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


def pydantic_convert(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        args_list = []
        if args:
            # 处理位置参数
            sig = inspect.signature(func)
            parameters = sig.parameters
            parameters_args = [
                parameter for parameter in parameters.values() if parameter.kind <= parameter.VAR_POSITIONAL
            ]
            try:
                args_list = list(args)
                for i, (arg, parameter) in enumerate(zip(args, parameters_args)):
                    # 使用 pydantic 解析参数，并将其转换为注解中指定的类型
                    if parameter.annotation is not inspect.Parameter.empty:
                        args_list[i] = TypeAdapter(parameter.annotation).validate_python(arg)
            except Exception as e:
                raise ValueError(f"Invalid argument type: {e}")

        if kwargs:
            # 获取函数的注解
            annotations = inspect.get_annotations(func)
            try:
                # 处理关键字参数
                for k, v in kwargs.items():
                    if k in annotations:
                        # 同样使用 pydantic 解析关键字参数
                        kwargs[k] = TypeAdapter(annotations[k]).validate_python(v)
            except Exception as e:
                raise ValueError(f"Invalid keyword argument type for {k}: {e}")

        # 调用原始函数，传递转换后的参数
        return await func(*args_list, **kwargs)

    return wrapper

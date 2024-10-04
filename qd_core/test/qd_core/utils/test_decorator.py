# test_decorator.py
import asyncio
import logging
import threading
from unittest.mock import MagicMock, patch

import pytest

from qd_core.utils.decorator import FunctionCache, MethodCache, log_and_raise_error

# 设置测试用的error_message_format
error_message_format = "Error occurred: {}"

# 设置测试用的log_level
log_level = logging.ERROR

# 设置测试用的logger
logger = MagicMock(spec=logging.Logger)


# 测试用的函数，用于被装饰
def log_and_raise_error_test_function():
    raise ValueError("Test error")


@pytest.mark.asyncio
# 测试用的异步函数，用于被装饰
async def log_and_raise_error_test_async_function():
    raise ValueError("Test error")


@pytest.fixture
def settings():
    # 设置测试用的配置，特别是log.traceback_print
    with patch("qd_core.config.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.log = MagicMock(traceback_print=True)
        mock_get_settings.return_value = mock_settings
        yield mock_settings


def test_log_and_raise_error_sync(settings):
    # 测试同步函数的情况
    decorated_function = log_and_raise_error(logger, error_message_format)(log_and_raise_error_test_function)

    with pytest.raises(ValueError) as excinfo:
        decorated_function()

    assert str(excinfo.value) == "Test error"
    logger.log.assert_called_once_with(log_level, error_message_format, "Test error", exc_info=True)
    logger.log.reset_mock()


@pytest.mark.asyncio
async def test_log_and_raise_error_async(settings):
    # 测试异步函数的情况
    decorated_async_function = log_and_raise_error(logger, error_message_format)(
        log_and_raise_error_test_async_function
    )

    with pytest.raises(ValueError) as excinfo:
        await decorated_async_function()

    assert str(excinfo.value) == "Test error"
    logger.log.assert_called_once_with(log_level, error_message_format, "Test error", exc_info=True)
    logger.log.reset_mock()


def test_log_and_raise_error_no_exception(settings):
    # 测试不抛出异常的情况
    decorated_function = log_and_raise_error(logger, error_message_format, raise_exception=False)(
        log_and_raise_error_test_function
    )

    result = decorated_function()

    assert result is None
    logger.log.assert_called_once_with(log_level, error_message_format, "Test error", exc_info=True)
    logger.log.reset_mock()


@pytest.mark.asyncio
async def test_log_and_raise_error_no_exception_async(settings):
    # 测试不抛出异常的情况（异步函数）
    decorated_async_function = log_and_raise_error(logger, error_message_format, raise_exception=False)(
        log_and_raise_error_test_async_function
    )

    result = await decorated_async_function()

    assert result is None
    logger.log.assert_called_once_with(log_level, error_message_format, "Test error", exc_info=True)
    logger.log.reset_mock()


# 假设的函数
def add(*args, sql_session=None, **kwargs):
    return sum(list(args) + list(kwargs.values()))


async def async_add(*args, sql_session=None, **kwargs):
    return sum(list(args) + list(kwargs.values()))


class MyClass:
    @MethodCache()
    def add(self, *args, sql_session=None, **kwargs):
        return sum(list(args) + list(kwargs.values()))

    @MethodCache()
    async def async_add(self, *args, sql_session=None, **kwargs):
        return sum(list(args) + list(kwargs.values()))


# 测试用例
class TestCache:
    def test_function_cache(self):
        # 测试 FunctionCache
        func_cache_instance = FunctionCache()
        cached_func = func_cache_instance(add)
        result1 = cached_func(3, 4)
        assert result1 == 7
        assert len(func_cache_instance._cache) == 1  # 检查缓存中有1个条目

        result2 = cached_func(3, 4)
        assert result2 == 7
        assert len(func_cache_instance._cache) == 1  # 再次检查缓存中有1个条目

    def test_function_cache_with_sql_session(self):
        # 测试 FunctionCache 带有 sql_session 参数
        func_cache_instance = FunctionCache()
        cached_func = func_cache_instance(add)
        result1 = cached_func(3, 4, sql_session="session")
        assert result1 == 7
        assert len(func_cache_instance._cache) == 0  # 检查缓存中没有条目

        result2 = cached_func(3, 4, sql_session="session")
        assert result2 == 7
        assert len(func_cache_instance._cache) == 0  # 再次检查缓存中没有条目

    @pytest.mark.asyncio
    async def test_async_function_cache(self):
        # 测试异步 FunctionCache
        func_cache_instance = FunctionCache()
        cached_async_func = func_cache_instance(async_add)
        result1 = await cached_async_func(7, 8)
        assert result1 == 15
        assert len(func_cache_instance._cache) == 1  # 检查缓存中有1个条目

        result2 = await cached_async_func(7, 8)
        assert result2 == 15
        assert len(func_cache_instance._cache) == 1  # 再次检查缓存中有1个条目

    @pytest.mark.asyncio
    async def test_async_function_cache_with_sql_session(self):
        # 测试异步 FunctionCache 带有 sql_session 参数
        func_cache_instance = FunctionCache()
        cached_async_func = func_cache_instance(async_add)
        result1 = await cached_async_func(7, 8, sql_session="session")
        assert result1 == 15
        assert len(func_cache_instance._cache) == 0  # 检查缓存中没有条目

        result2 = await cached_async_func(7, 8, sql_session="session")
        assert result2 == 15
        assert len(func_cache_instance._cache) == 0  # 再次检查缓存中没有条目

    def test_method_cache(self):
        # 测试 MethodCache
        obj = MyClass()
        result1 = obj.add(3, 4)
        assert result1 == 7
        assert len(obj._cache) == 1  # 检查缓存中有1个条目

        result2 = obj.add(3, 4)
        assert result2 == 7
        assert len(obj._cache) == 1  # 再次检查缓存中有1个条目

    def test_method_cache_with_sql_session(self):
        # 测试 MethodCache 带有 sql_session 参数
        obj = MyClass()
        result1 = obj.add(3, 4, sql_session="session")
        assert result1 == 7
        assert not hasattr(obj, "_cache")  # 检查不存在缓存 _cache 属性

        result2 = obj.add(3, 4, sql_session="session")
        assert result2 == 7
        assert not hasattr(obj, "_cache")  # 检查不存在缓存 _cache 属性

    @pytest.mark.asyncio
    async def test_async_method_cache(self):
        # 测试异步 MethodCache
        obj = MyClass()
        result1 = await obj.async_add(7, 8)
        assert result1 == 15
        assert len(obj._cache) == 1  # 检查缓存中有1个条目

        result2 = await obj.async_add(7, 8)
        assert result2 == 15
        assert len(obj._cache) == 1  # 再次检查缓存中有1个条目

    @pytest.mark.asyncio
    async def test_async_method_cache_with_sql_session(self):
        # 测试异步 MethodCache 带有 sql_session 参数
        obj = MyClass()
        result1 = await obj.async_add(7, 8, sql_session="session")
        assert result1 == 15
        assert not hasattr(obj, "_cache")  # 检查缓存中没有条目

        result2 = await obj.async_add(7, 8, sql_session="session")
        assert result2 == 15
        assert not hasattr(obj, "_cache")  # 再次检查缓存中没有条目

    def test_multithreading_function_cache(self):
        # 测试多线程 FunctionCache
        func_cache_instance = FunctionCache()
        cached_func = func_cache_instance(add)

        results = []
        threads = []

        def thread_func():
            result = cached_func(3, 4)
            results.append(result)

        for _ in range(10):
            t = threading.Thread(target=thread_func)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert all(r == 7 for r in results)
        assert len(func_cache_instance._cache) == 1  # 检查缓存中有1个条目

    @pytest.mark.asyncio
    async def test_async_concurrency_function_cache(self):
        # 测试异步并发 FunctionCache
        func_cache_instance = FunctionCache()
        cached_async_func = func_cache_instance(async_add)

        results = await asyncio.gather(*[cached_async_func(7, 8) for _ in range(10)])

        assert all(r == 15 for r in results)
        assert len(func_cache_instance._cache) == 1  # 检查缓存中有1个条目

    def test_multithreading_method_cache(self):
        # 测试多线程 MethodCache
        obj = MyClass()
        results = []
        threads = []

        def thread_func():
            result = obj.add(3, 4)
            results.append(result)

        for _ in range(10):
            t = threading.Thread(target=thread_func)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert all(r == 7 for r in results)
        assert len(obj._cache) == 1  # 检查缓存中有1个条目

    @pytest.mark.asyncio
    async def test_async_concurrency_method_cache(self):
        # 测试异步并发 MethodCache
        obj = MyClass()
        results = await asyncio.gather(*[obj.async_add(7, 8) for _ in range(10)])

        assert all(r == 15 for r in results)
        assert len(obj._cache) == 1  # 检查缓存中有1个条目


if __name__ == "__main__":
    pytest.main()

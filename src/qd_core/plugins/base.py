import os
import subprocess
import sys
from functools import partial, wraps
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import APIRouter
from plux import FunctionPlugin, PluginSpec  # type: ignore
from pydantic_settings import BaseSettings

from qd_core.utils.decorator import pydantic_convert
from qd_core.utils.log import Log

logger_plugins = Log("QD.Plugins").getlogger()
router = APIRouter()


def add_api_routes(
    api_paths: List[str],
    fn: Callable,
    api_methods: List[List[str]],
    api_kwargs: Dict = {},
    api_router: Optional[APIRouter] = None,
    api_router_kwargs: Dict = {},
):
    if not api_router:
        _api_router = router
    else:
        _api_router = api_router
    for api_path, api_method in zip(api_paths, api_methods):
        _api_router.add_api_route(api_path, fn, methods=api_method, **api_kwargs)
    if api_router:
        router.include_router(_api_router, **api_router_kwargs)


def api_function_plugin(
    namespace: str,
    name: Optional[str] = None,
    api_paths: Optional[List[str]] = None,
    api_methods: Optional[List[List[str]]] = None,
    api_kwargs: Optional[Dict[str, Any]] = None,
    api_router: Optional[APIRouter] = None,
    api_router_kwargs: Optional[Dict[str, Any]] = None,
    should_load: Optional[Union[bool, Callable[[], bool]]] = None,
    load: Optional[Callable] = None,
    settings: Optional[BaseSettings] = None,
):
    """
    A combined decorator that both exposes a function as a discoverable and loadable FunctionPlugin
    and sets up API routing for the function if API-related parameters are provided.
    """
    if api_kwargs is None:
        api_kwargs = {}
    if api_router_kwargs is None:
        api_router_kwargs = {}
    if settings is None:
        settings = BaseSettings()

    def wrapper(fn):
        plugin_name = name or fn.__name__
        fn = pydantic_convert(fn)

        @wraps(fn)
        def factory():
            # Set up API routes if API paths and methods are provided
            if api_paths and api_methods:
                _load = partial(
                    add_api_routes,
                    api_paths,
                    fn,
                    api_methods=api_methods,
                    api_kwargs=api_kwargs,
                    api_router=api_router,
                    api_router_kwargs=api_router_kwargs,
                )

            # Create and attach the FunctionPlugin
            fn_plugin = FunctionPlugin(
                fn,
                should_load=should_load,
                load=_load or load,
            )
            fn_plugin.namespace = namespace
            fn_plugin.name = plugin_name

            return fn_plugin

        # Attach the plugin spec to the function for discovery
        fn.__pluginspec__ = PluginSpec(namespace, plugin_name, factory)

        return fn

    return wrapper

def set_env_variable_and_run_command(command: List[str], envs: Optional[Dict[str, str]] = None):
    """
    设置环境变量并运行给定的命令，确保环境变量在子进程中生效。
    这个函数通过直接操作环境变量而不是依赖shell来提高安全性。
    """
    # 参数验证
    if not isinstance(command, list):
        logger_plugins.error("命令必须以列表形式提供。")
        raise ValueError("命令必须以列表形式提供。")

    # 复制当前环境变量并更新
    env = dict(os.environ)
    if envs:
        if not isinstance(envs, dict):
            logger_plugins.error("环境变量必须以字典形式提供。")
            raise ValueError("环境变量必须以字典形式提供。")
        logger_plugins.info(f"设置环境变量: {envs}")
        env.update(envs)

    try:
        # 使用Popen手动设置环境变量并执行命令，以确保环境变量在子进程中生效
        process = subprocess.Popen(command, shell=False, env=env)
        process.wait()
        return process.returncode  # 返回命令执行的状态码
    except OSError as e:
        logger_plugins.error(f"执行命令时发生OS错误: {e}")
        return -1  # 表明执行出错
    except ValueError as e:
        logger_plugins.error(f"无效的命令或环境变量设置: {e}")
        return -1  # 表明执行出错


def entrypoints(args=None):
    command = [sys.executable, "-m", "plux", "entrypoints"]

    # 判断 python 版本是否小于 3.12, 是则设置 SETUPTOOLS_USE_DISTUTILS 环境变量为 stdlib
    if sys.version_info < (3, 12):
        return set_env_variable_and_run_command(command, {"SETUPTOOLS_USE_DISTUTILS": "stdlib"})
    else:
        return set_env_variable_and_run_command(command)

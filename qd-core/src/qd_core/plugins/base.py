import asyncio
import sys
from functools import partial, wraps
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import APIRouter
from plux import FunctionPlugin, PluginSpec  # type: ignore
from pydantic import validate_call
from pydantic_settings import BaseSettings

from qd_core.utils.i18n import gettext

# from pydantic.config import ConfigDict
from qd_core.utils.log import Log
from qd_core.utils.shell import set_env_variable_and_run_command

logger_plugins = Log("QD.Core.Plugins").getlogger()
router = APIRouter()


def add_api_routes(
    path_list: List[str],
    function: Callable,
    method_list: List[List[str]],
    router_kwargs: Dict = {},
    custom_router: Optional[APIRouter] = None,
    router_inclusion_kwargs: Dict = {},
):
    """
    Adds API routes to the FastAPI router.
    """
    target_router = custom_router or router
    for path, methods in zip(path_list, method_list):
        target_router.add_api_route(path, function, methods=methods, **router_kwargs)
        logger_plugins.debug(gettext("Added API route: {path} {methods}").format(path=path, methods=methods))
    if custom_router:
        router.include_router(custom_router, **router_inclusion_kwargs)


def api_function_plugin(
    namespace: str,
    name: Optional[str] = None,
    path_list: Optional[List[str]] = None,
    method_list: Optional[List[List[str]]] = None,
    router_kwargs: Optional[Dict[str, Any]] = None,
    custom_router: Optional[APIRouter] = None,
    router_inclusion_kwargs: Optional[Dict[str, Any]] = None,
    should_load: Optional[Union[bool, Callable[[], bool]]] = None,
    load_function: Optional[Callable] = None,
    settings: Optional[BaseSettings] = None,
    # TODO: 启用并测试 validate 配置
    # validate_config: Optional[ConfigDict] = None,
    # validate_return: bool = False,
):
    """
    A combined decorator that both exposes a function as a discoverable and loadable FunctionPlugin
    and sets up API routing for the function if API-related parameters are provided.
    """
    router_kwargs = router_kwargs or {}
    router_inclusion_kwargs = router_inclusion_kwargs or {}
    settings = settings or BaseSettings()

    def decorator(function: Callable):
        plugin_name = name or function.__name__
        validated_function = validate_call(
            function,
            # config=validate_config,
            # validate_return=validate_return
        )

        @wraps(validated_function)
        def plugin_factory():
            # Set up API routes if API paths and methods are provided
            if path_list and method_list:
                route_setup_function = partial(
                    add_api_routes,
                    path_list,
                    validated_function,
                    method_list=method_list,
                    router_kwargs=router_kwargs,
                    custom_router=custom_router,
                    router_inclusion_kwargs=router_inclusion_kwargs,
                )
            else:
                route_setup_function = None

            # Create and attach the FunctionPlugin

            plugin = FunctionPlugin(
                validated_function,
                should_load=should_load,
                load=route_setup_function or load_function,
            )
            plugin.namespace = namespace
            plugin.name = plugin_name

            return plugin

        # Attach the plugin spec to the function for discovery
        function.__pluginspec__ = PluginSpec(namespace, plugin_name, plugin_factory)  # type: ignore
        return function

    return decorator


def entrypoints(args=None):
    command = [sys.executable, "-m", "plux", "entrypoints"]

    # 判断 python 版本是否小于 3.12, 是则设置 SETUPTOOLS_USE_DISTUTILS 环境变量为 stdlib
    if sys.version_info < (3, 12):
        return asyncio.run(set_env_variable_and_run_command(command, {"SETUPTOOLS_USE_DISTUTILS": "stdlib"}))
    else:
        return asyncio.run(set_env_variable_and_run_command(command))

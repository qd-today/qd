import asyncio
import importlib.metadata as importlib_metadata
import logging
import sys
import time
from typing import Dict

from pip._internal.req.constructors import install_req_from_line
from plux import Plugin, PluginManager  # type: ignore

from qd_core.utils.shell import run_command_and_log_output_async

logger = logging.getLogger(__name__)


class QDPluginManager:
    def __init__(self, namespace: str, strict_default_plugins: bool = True):
        self.namespace = namespace
        self.plugin_manager = PluginManager(namespace)
        self._default_plugins_manger = PluginManager("qd.plugins.default")
        self._strict_default_plugins = strict_default_plugins
        self.enabled_plugins: Dict[str, Plugin] = {}
        for plugin in self._default_plugins_manger._plugins.keys():
            self.enable_plugin(plugin)

    def _is_default_plugin(self, plugin_name):
        # 检查插件是否为默认插件
        return plugin_name in self._default_plugins_manger._plugins.keys()

    async def install_plugin(self, plugin_name_or_vcs):
        # 处理模块名或远程仓库的安装
        try:
            # 使用 pip 命令解析仓库中的包名
            plugin_name = install_req_from_line(plugin_name_or_vcs).name

            # 检查模块是否已安装
            try:
                installed = importlib_metadata.distribution(plugin_name)
            except importlib_metadata.PackageNotFoundError:
                installed = False
            if installed:
                logger.info("Plugin '%s' is already installed.", plugin_name)
                return True

            # 异步安装模块并记录输出日志
            return_code = await run_command_and_log_output_async(
                sys.executable, "-m", "pip", "install", plugin_name_or_vcs
            )

            # 判断安装是否成功
            if return_code == 0:
                logger.info("Plugin '%s' has been installed.", plugin_name)
                return True
            else:
                logger.error("Failed to install plugin '%s'. Return code: %d", plugin_name, return_code)
                return False

        except Exception as e:
            logger.error("Failed to install plugin '%s': %s", plugin_name, e)
            raise

    async def start_plugin(self, plugin_name):
        # 加载并启动插件
        try:
            # 检查插件是否已启用
            if plugin_name not in self.enabled_plugins:
                self.enable_plugin(plugin_name)

            # 获取插件实例并启动
            plugin = self.enabled_plugins[plugin_name]
            if hasattr(plugin, "start"):
                plugin.start()  # 假设插件有一个 start 方法用于启动
            else:
                logger.warning("Plugin '%s' does not have a start method.", plugin_name)
        except Exception as e:
            logger.error("Failed to start plugin '%s': %s", plugin_name, e)
            raise

    def enable_plugin(self, plugin_name, default=False):
        # 启用插件
        if plugin_name in self.enabled_plugins:
            logger.info("Plugin '%s' is already enabled.", plugin_name)
            return

        # 使用 plux 加载插件
        if default or (self._strict_default_plugins and self._is_default_plugin(plugin_name)):
            plugin = self._default_plugins_manger.load(plugin_name)
        else:
            plugin = self.plugin_manager.load(plugin_name)
        if plugin:
            self.enabled_plugins[plugin_name] = plugin
            logger.info("Plugin '%s' has been enabled.", plugin_name)
        else:
            logger.error("Failed to load plugin '%s'.", plugin_name)
            raise Exception("Failed to load plugin '%s'.", plugin_name)

    def disable_plugin(self, plugin_name):
        # 禁用插件
        if plugin_name not in self.enabled_plugins:
            logger.info("Plugin '%s' is already disabled.", plugin_name)
            return
        if self._is_default_plugin(plugin_name):
            logger.error("Default plugin '%s' cannot be disabled.", plugin_name)
            return

        self.enabled_plugins.pop(plugin_name)
        logger.info("Plugin '%s' has been disabled.", plugin_name)

    async def uninstall_plugin(self, plugin_name):
        # 卸载插件
        if self._is_default_plugin(plugin_name):
            logger.error("Default plugin '%s' cannot be uninstalled.", plugin_name)
            raise Exception("Default plugin '%s' cannot be uninstalled.", plugin_name)

        # 检查插件是否已安装
        try:
            installed = importlib_metadata.distribution(plugin_name)
        except importlib_metadata.PackageNotFoundError:
            installed = False
        if not installed:
            logger.info("Plugin '%s' is not installed.", plugin_name)
            return

        # 异步执行插件卸载并记录输出日志
        return_code = await run_command_and_log_output_async(
            sys.executable, "-m", "pip", "uninstall", "-y", plugin_name
        )

        # 判断卸载是否成功
        if return_code == 0:
            logger.info("Plugin '%s' has been uninstalled.", plugin_name)
        else:
            logger.error("Failed to uninstall plugin '%s'. Return code: %d", plugin_name, return_code)


async def test_default():
    qdpm = QDPluginManager("qd.plugins")
    s_t = time.time()
    await qdpm.enabled_plugins["util-delay"](-2)
    duration = time.time() - s_t
    print(f"delay 2 seconds, duration: {duration}s")


# 示例用法
if __name__ == "__main__":
    asyncio.run(test_default())
    print()

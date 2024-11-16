import asyncio
import os
from gettext import gettext
from typing import Dict, List, Optional

from qd_core.utils.log import Log

logger = Log("QD.Core.Utils").getlogger()


async def run_command_and_log_output_async(command, *args, **kwargs):
    try:
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # 将stderr重定向到stdout，便于统一处理
            **kwargs,
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break  # 当没有更多输出时，跳出循环
            decoded_line = line.decode().rstrip()  # 解码并移除末尾换行符
            logger.info(decoded_line)  # 记录输出日志

        await process.wait()  # 等待命令执行完成
        return process.returncode

    except Exception as e:
        logger.error(gettext("An error occurred during command execution: {e}").format(e=e))
        return -1  # 假设出现异常时返回码为-1（可根据实际情况调整）


async def set_env_variable_and_run_command(command: List[str], envs: Optional[Dict[str, str]] = None):
    """
    设置环境变量并运行给定的命令，确保环境变量在子进程中生效。
    这个函数通过直接操作环境变量而不是依赖shell来提高安全性。
    """
    # 参数验证
    if not isinstance(command, list):
        logger.error(gettext("命令必须以列表形式提供。"))
        raise ValueError(gettext("命令必须以列表形式提供。"))

    # 复制当前环境变量并更新
    env = dict(os.environ)
    if envs:
        if not isinstance(envs, dict):
            logger.error(gettext("环境变量必须以字典形式提供。"))
            raise ValueError(gettext("环境变量必须以字典形式提供。"))
        logger.info(gettext("设置环境变量: {envs}").format(envs=envs))
        env.update(envs)

    try:
        # 使用Popen手动设置环境变量并执行命令，以确保环境变量在子进程中生效
        return await run_command_and_log_output_async(*command, shell=False, env=env)
    except OSError as e:
        logger.error(gettext("执行命令时发生OS错误: {e}").format(e=e))
        return -1  # 表明执行出错
    except ValueError as e:
        logger.error(gettext("无效的命令或环境变量设置: {e}").format(e=e))
        return -1  # 表明执行出错

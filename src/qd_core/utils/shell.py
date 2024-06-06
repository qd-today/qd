import asyncio

from qd_core.utils.log import Log

logger = Log(__name__).getlogger()


async def run_command_and_log_output_async(command, *args):
    try:
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # 将stderr重定向到stdout，便于统一处理
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
        logger.error(f"An error occurred during command execution: {e}")
        return -1  # 假设出现异常时返回码为-1（可根据实际情况调整）

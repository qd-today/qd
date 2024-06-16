import argparse
import asyncio
import json
import os
import time

from qd_core.client.fetcher import Fetcher
from qd_core.config import get_settings
from qd_core.plugins.manager import QDPluginManager
from qd_core.utils.log import Log

logger_qd = Log("QD.Cli").getlogger()


async def fetch_har_with_env(har_tpl, env):
    starttime = time.perf_counter()
    QDPluginManager("qd.plugins")
    logger_qd.info("加载插件耗时: %ss", time.perf_counter() - starttime)
    fetcher = Fetcher()
    env, _ = await fetcher.do_fetch(har_tpl, env)
    return env


def load_json_file(file_path, encoding="utf-8"):
    """
    安全地加载并解析指定编码的JSON文件。
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        with open(file_path, encoding=encoding) as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(f"无法解析JSON: {file_path}") from e


def fetch_har_tpl_file(har_tpl_file, env_json=None, har_encoding="utf-8", env_encoding="utf-8", **kwargs):
    # 加载HAR模板
    har_tpl = load_json_file(har_tpl_file, encoding=har_encoding)

    # 加载环境配置并直接合并额外的参数
    env = {} if env_json is None else load_json_file(env_json, encoding=env_encoding)
    env.setdefault("variables", {}).update(kwargs)  # 直接合并kwargs
    env.setdefault("session", [])

    try:
        env = asyncio.run(fetch_har_with_env(har_tpl, env))
    except Exception as e:
        logger_qd.error(
            "QD 执行失败: %s", str(e).replace("\\r\\n", "\r\n"), exc_info=get_settings().log.traceback_print
        )
    else:
        logger_qd.info("QD 执行成功！结果:\n %s", env.get("variables", {}).get("__log__", "").replace("\\r\\n", "\r\n"))


def fetch_har_cli():
    parser = argparse.ArgumentParser(description="使用 QD 执行 HAR 模板请求。")

    parser.add_argument(
        "har_tpl",
        metavar="HAR_TPL_PATH",
        help="HAR 模板文件路径。\n示例: ./example.tpl.har",
    )

    parser.add_argument(
        "-E",
        "--env-json",
        metavar="ENV_JSON_PATH",
        help="模板变量配置 Json 文件路径(可选)。\n示例: ./env_config.json",
    )

    parser.add_argument(
        "-k",
        "--variable",
        action="append",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="额外的键值对，用于添加或更新模板变量值(可选)。\n"
        "支持添加多个模板变量键值对。\n"
        '示例: -k Cookie "session=123456; token=abcdef" --variable ENDPOINT https://api.example.com',
    )

    parser.add_argument(
        "--har-encoding",
        default="utf-8",
        help="HAR 模板文件的字符编码 (可选)，默认为 utf-8。",
    )

    parser.add_argument(
        "--env-encoding",
        default="utf-8",
        help="模板变量配置 Json 文件的字符编码 (可选)，默认为 utf-8。",
    )

    args = parser.parse_args()

    extra_vars = dict(args.variable) if args.variable else {}
    fetch_har_tpl_file(
        args.har_tpl, args.env_json, har_encoding=args.har_encoding, env_encoding=args.env_encoding, **extra_vars
    )


if __name__ == "__main__":
    fetch_har_cli()

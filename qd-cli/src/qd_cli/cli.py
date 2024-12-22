import argparse
import asyncio
import json
import os
import time

from qd_core.config import get_settings
from qd_core.utils.i18n import get_translation
from qd_core.utils.log import Log

logger_qd = Log("QD.Cli").getlogger()

CLI_TRANSLATION = get_translation(os.path.join(os.path.dirname(__file__), "locale"))


def gettext(message):
    return CLI_TRANSLATION.gettext(message)


async def fetch_har_with_env(har_tpl, env):
    logger_qd.debug(gettext("Loading QD plugins..."))
    starttime = time.perf_counter()
    from qd_core.client.fetcher import Fetcher
    from qd_core.plugins.manager import QDPluginManager

    QDPluginManager("qd.plugins")
    logger_qd.debug(gettext("Loading plugins completed in %.3f seconds."), time.perf_counter() - starttime)
    fetcher = Fetcher()
    env, _ = await fetcher.do_fetch(har_tpl, env)
    return env


def load_json_file(file_path, encoding="utf-8"):
    """
    Safely load and parse JSON file with specified encoding.

    :param file_path: JSON file path
    :param encoding: JSON file encoding
    :return: JSON data
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(gettext("File not found: {file_path}").format(file_path=file_path))

    try:
        with open(file_path, encoding=encoding) as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(gettext("Unable to parse JSON: {file_path}").format(file_path=file_path)) from e


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
            gettext("QD execution failed: %s"),
            str(e).replace("\\r\\n", "\r\n"),
            exc_info=get_settings().log.traceback_print,
        )
    else:
        logger_qd.info(
            gettext("QD execution succeeded! Result:\n %s"), env.variables.get("__log__", "").replace("\\r\\n", "\r\n")
        )


def fetch_har_cli():
    parser = argparse.ArgumentParser(description=gettext("Execute HAR template requests using QD."))

    parser.add_argument(
        "har_tpl",
        metavar="HAR_TPL_PATH",
        help=gettext("HAR template file path.\nExample: ./example.tpl.har"),
    )

    parser.add_argument(
        "-E",
        "--env-json",
        metavar="ENV_JSON_PATH",
        help=gettext("Template variable configuration JSON file path (optional).\nExample: ./env_config.json"),
    )

    parser.add_argument(
        "-k",
        "--variable",
        action="append",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help=gettext(
            "Extra key-value pairs for adding or updating template variable values (optional).\n"
            "Support adding multiple template variable key-value pairs.\n"
            'Example: -k Cookie "session=123456; token=abcdef" --variable ENDPOINT https://api.example.com'
        ),
    )

    parser.add_argument(
        "--har-encoding",
        default="utf-8",
        help=gettext("Character encoding of HAR template file (optional), default is utf-8."),
    )

    parser.add_argument(
        "--env-encoding",
        default="utf-8",
        help=gettext("Character encoding of template variable configuration JSON file (optional), default is utf-8."),
    )

    args = parser.parse_args()

    extra_vars = dict(args.variable) if args.variable else {}
    fetch_har_tpl_file(
        args.har_tpl, args.env_json, har_encoding=args.har_encoding, env_encoding=args.env_encoding, **extra_vars
    )


if __name__ == "__main__":
    fetch_har_cli()

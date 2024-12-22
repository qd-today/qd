import random
import re
import time
from typing import Iterable, Tuple

from qd_core.client.http.handler import HttpHandler
from qd_core.config import get_settings
from qd_core.schemas.har import HAR, Env
from qd_core.utils.i18n import gettext
from qd_core.utils.log import Log
from qd_core.utils.safe_eval import safe_eval

logger_fetcher = Log("QD.Core.Client").getlogger()


class Fetcher:
    FOR_START = re.compile(r"{%\s*for\s+(\w+)\s+in\s+(\w+|list\([\s\S]*\)|range\([\s\S]*\))\s*%}")
    IF_START = re.compile(r"{%\s*if\s+(.+)\s*%}")
    WHILE_START = re.compile(r"{%\s*while\s+(.+)\s*%}")
    ELSE_START = re.compile(r"{%\s*else\s*%}")
    PARSE_END = re.compile(r"{%\s*end(for|if|while)\s*%}")

    def __init__(self, **kwargs):
        self.http_handler = HttpHandler(**kwargs)

    def parse_har_template(self, har_template):
        stmt_stack = []

        def __append(entry):
            if stmt_stack[-1]["type"] == "if":
                stmt_stack[-1][stmt_stack[-1]["parse"]].append(entry)
            elif stmt_stack[-1]["type"] == "for" or stmt_stack[-1]["type"] == "while":
                stmt_stack[-1]["body"].append(entry)

        for i, entry in enumerate(har_template):
            if "type" in entry:
                yield entry
            elif self.FOR_START.match(entry["request"]["url"]):
                m = self.FOR_START.match(entry["request"]["url"])
                stmt_stack.append(
                    {
                        "type": "for",
                        "target": m.group(1),
                        "from": m.group(2),
                        "body": [],
                        "idx": entry["idx"],
                    }
                )
            elif self.WHILE_START.match(entry["request"]["url"]):
                m = self.WHILE_START.match(entry["request"]["url"])
                stmt_stack.append(
                    {
                        "type": "while",
                        "condition": m.group(1),
                        "body": [],
                        "idx": entry["idx"],
                    }
                )
            elif self.IF_START.match(entry["request"]["url"]):
                m = self.IF_START.match(entry["request"]["url"])
                stmt_stack.append(
                    {
                        "type": "if",
                        "condition": m.group(1),
                        "parse": "true",
                        "true": [],
                        "false": [],
                        "idx": entry["idx"],
                    }
                )
            elif self.ELSE_START.match(entry["request"]["url"]):
                stmt_stack[-1]["parse"] = "false"
            elif self.PARSE_END.match(entry["request"]["url"]):
                m = self.PARSE_END.match(entry["request"]["url"])
                entry_type = stmt_stack and stmt_stack[-1]["type"]
                if entry_type == "for" or entry_type == "if" or entry_type == "while":
                    if m.group(1) != entry_type:
                        raise Exception(
                            f"Failed at {i+1}/{len(har_template)} end tag \\r\\n"
                            f"Error: End tag should be \"end{stmt_stack[-1]['type']}\", but \"end{m.group(1)}\""
                        )
                    entry = stmt_stack.pop()
                    if stmt_stack:
                        __append(entry)
                    else:
                        yield entry
            elif stmt_stack:
                __append(
                    {
                        "type": "request",
                        "entry": entry,
                    }
                )
            else:
                yield {
                    "type": "request",
                    "entry": entry,
                }

        while stmt_stack:
            yield stmt_stack.pop()

    async def do_fetch(
        self, har_template, env: Env, proxies=None, request_limit=get_settings().task.task_request_limit, tpl_length=0
    ) -> Tuple[Env, int]:
        """
        do a fetch of hole har template
        """
        if proxies:
            proxy = random.choice(proxies)
        elif get_settings().proxy.proxies:
            proxy = random.choice(get_settings().proxy.proxies)
        else:
            proxy = {}

        if tpl_length == 0 and len(har_template) > 0:
            tpl_length = len(har_template)
            for i, entry in enumerate(har_template):
                entry["idx"] = i + 1

        for i, block in enumerate(self.parse_har_template(har_template)):
            if request_limit <= 0:
                raise Exception("request limit")
            elif block["type"] == "for":
                support_enum = False
                _from_var = block["from"]
                _from = env.variables.get(_from_var, [])
                try:
                    if isinstance(_from_var, str) and _from_var.startswith("list(") or _from_var.startswith("range("):
                        _from = safe_eval(_from_var, env.variables)
                    if not isinstance(_from, Iterable):
                        raise Exception(gettext("'For' loop only supports iterated types and variables"))
                    support_enum = True
                except Exception as e:
                    if get_settings().log.debug:
                        logger_fetcher.exception(e)
                if support_enum:
                    env.variables["loop_length"] = str(len(_from))
                    env.variables["loop_depth"] = str(int(env.variables.get("loop_depth", "0")) + 1)
                    env.variables["loop_depth0"] = str(int(env.variables.get("loop_depth0", "-1")) + 1)
                    for idx, each in enumerate(_from):
                        env.variables[block["target"]] = each
                        if idx == 0:
                            env.variables["loop_first"] = "True"
                            env.variables["loop_last"] = "False"
                        elif idx == len(_from) - 1:
                            env.variables["loop_first"] = "False"
                            env.variables["loop_last"] = "True"
                        else:
                            env.variables["loop_first"] = "False"
                            env.variables["loop_last"] = "False"
                        env.variables["loop_index"] = str(idx + 1)
                        env.variables["loop_index0"] = str(idx)
                        env.variables["loop_revindex"] = str(len(_from) - idx)
                        env.variables["loop_revindex0"] = str(len(_from) - idx - 1)
                        env, request_limit = await self.do_fetch(
                            block["body"], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length
                        )
                    env.variables["loop_depth"] = str(int(env.variables.get("loop_depth", "0")) - 1)
                    env.variables["loop_depth0"] = str(int(env.variables.get("loop_depth0", "-1")) - 1)
                else:
                    for each in _from:
                        env.variables[block["target"]] = each
                        env, request_limit = await self.do_fetch(
                            block["body"], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length
                        )
            elif block["type"] == "while":
                start_time = time.perf_counter()
                env.variables["loop_depth"] = str(int(env.variables.get("loop_depth", "0")) + 1)
                env.variables["loop_depth0"] = str(int(env.variables.get("loop_depth0", "-1")) + 1)
                while_idx = 0
                while time.perf_counter() - start_time <= get_settings().task.task_while_loop_timeout:
                    env.variables["loop_index"] = str(while_idx + 1)
                    env.variables["loop_index0"] = str(while_idx)
                    try:
                        condition = safe_eval(block["condition"], env.variables)
                    except NameError:
                        condition = False
                    except ValueError as e:
                        if len(str(e)) > 20 and str(e)[:20] == "<class 'NameError'>:":
                            condition = False
                        else:
                            str_e = str(e).replace("<class 'ValueError'>", "ValueError")
                            raise Exception(
                                gettext(
                                    "Failed at {block_idx}/{tpl_length} while condition, \\r\\n"
                                    "Error: {error}, \\r\\n"
                                    "Block condition: {condition}"
                                ).format(
                                    block_idx=block["idx"],
                                    tpl_length=tpl_length,
                                    error=str_e,
                                    condition=block["condition"],
                                )
                            ) from e
                    except Exception as e:
                        raise Exception(
                            gettext(
                                "Failed at {block_idx}/{tpl_length} while condition, \\r\\n"
                                "Error: {error}, \\r\\n"
                                "Block condition: {condition}"
                            ).format(
                                block_idx=block["idx"],
                                tpl_length=tpl_length,
                                error=e,
                                condition=block["condition"],
                            )
                        ) from e
                    if condition:
                        env, request_limit = await self.do_fetch(
                            block["body"], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length
                        )
                    else:
                        if get_settings().log.debug:
                            logger_fetcher.debug(
                                gettext("while loop break, time: %ss"), time.perf_counter() - start_time
                            )
                        break
                    while_idx += 1
                else:
                    raise Exception(
                        gettext(
                            "Failed at {block_idx}/{tpl_length} while end, \\r\\n"
                            "Error: while loop timeout, time: {elapsed_time}s \\r\\n"
                            "Block condition: {condition}"
                        ).format(
                            block_idx=block["idx"],
                            tpl_length=tpl_length,
                            elapsed_time=time.perf_counter() - start_time,
                            condition=block["condition"],
                        )
                    )
                env.variables["loop_depth"] = str(int(env.variables.get("loop_depth", "0")) - 1)
                env.variables["loop_depth0"] = str(int(env.variables.get("loop_depth0", "-1")) - 1)
            elif block["type"] == "if":
                try:
                    condition = safe_eval(block["condition"], env.variables)
                except NameError:
                    condition = False
                except ValueError as e:
                    if len(str(e)) > 20 and str(e)[:20] == "<class 'NameError'>:":
                        condition = False
                    else:
                        str_e = str(e).replace("<class 'ValueError'>", "ValueError")
                        raise Exception(
                            gettext(
                                "Failed at {block_idx}/{tpl_length} if condition, \\r\\n"
                                "Error: {error}, \\r\\n"
                                "Block condition: {condition}"
                            ).format(
                                block_idx=block["idx"],
                                tpl_length=tpl_length,
                                error=str_e,
                                condition=block["condition"],
                            )
                        ) from e
                except Exception as e:
                    raise Exception(
                        gettext(
                            "Failed at {block_idx}/{tpl_length} if condition, \\r\\n"
                            "Error: {error}, \\r\\n"
                            "Block condition: {condition}"
                        ).format(
                            block_idx=block["idx"],
                            tpl_length=tpl_length,
                            error=e,
                            condition=block["condition"],
                        )
                    ) from e
                if condition:
                    _, request_limit = await self.do_fetch(
                        block["true"], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length
                    )
                else:
                    _, request_limit = await self.do_fetch(
                        block["false"], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length
                    )
            elif block["type"] == "request":
                entry = block["entry"]
                try:
                    request_limit -= 1
                    result = await self.http_handler.do_request(
                        HAR(request=entry["request"], rule=entry["rule"], env=env),
                        proxy=proxy,
                    )
                    env = result.env
                    if result.success:
                        logger_fetcher.debug(
                            gettext("Success at %d/%d request, \r\nRequest URL: %s, \r\nResult: %s"),
                            entry["idx"],
                            tpl_length,
                            entry["request"]["url"],
                            env.variables.get("__log__", "").replace("\\r\\n", "\r\n"),
                        )
                except Exception as e:
                    if get_settings().log.debug:
                        logger_fetcher.exception(e)
                    raise Exception(
                        gettext(
                            "Failed at {block_idx}/{tpl_length} request, \\r\\n"
                            "Error: {error}, \\r\\n"
                            "Request URL: {request_url}"
                        ).format(
                            block_idx=entry["idx"],
                            tpl_length=tpl_length,
                            error=e,
                            request_url=entry["request"]["url"],
                        )
                    ) from e
                if not result.success:
                    raise Exception(
                        gettext(
                            "Failed at {block_idx}/{tpl_length} request, \\r\\n"
                            "{result_msg}, \\r\\n"
                            "Request URL: {request_url}"
                        ).format(
                            block_idx=entry["idx"],
                            tpl_length=tpl_length,
                            result_msg=result.msg,
                            request_url=entry["request"]["url"],
                        )
                    )

        return env, request_limit

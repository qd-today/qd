import ipaddress
import re

from jinja2 import Undefined

from qd_core.filters.convert import to_native, to_text


def is_lan(ip):
    try:
        return ipaddress.ip_address(ip.strip()).is_private
    except Exception:
        return False


def is_ip(addr=None):
    if addr:
        p = re.compile(
            r"""
         ((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # IPv4
         # IPv4 mapped / translated addresses
         |::ffff:(0:)?((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)
         # |fe80:(:[0-9a-fA-F]{1,4}){0,4}(%\w+)? # IPv6 link-local
         |([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4} # IPv6 full
         |(([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})?::(([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})? # IPv6 with ::
         """,
            re.VERBOSE,
        )
        tmp = p.match(addr)
        if tmp and tmp[0] == addr:
            if ":" in tmp[0]:
                return 6
            return 4
        return 0
    return 0


def is_num(value: str = ""):
    value = str(value)
    if value.count(".") == 1:
        tmp = value.split(".")
        return tmp[0].lstrip("-").isdigit() and tmp[1].isdigit()
    else:
        return value.lstrip("-").isdigit()


def mandatory(value, msg=None):
    """Make a variable mandatory"""
    if isinstance(value, Undefined):
        # pylint: disable=protected-access
        if value._undefined_name is not None:
            name = f"'{to_text(value._undefined_name)}' "
        else:
            name = ""

        if msg is not None:
            raise Exception(to_native(msg))
        raise Exception(f"Mandatory variable {name} not defined.")

    return value

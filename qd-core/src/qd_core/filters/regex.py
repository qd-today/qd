import re

from qd_core.filters.convert import to_text


def regex_replace(value="", pattern="", replacement="", count=0, ignorecase=False, multiline=False):
    """Perform a `re.sub` returning a string"""

    value = to_text(value, errors="surrogate_or_strict", nonstring="simplerepr")

    flags = 0
    if ignorecase:
        flags |= re.I
    if multiline:
        flags |= re.M
    _re = re.compile(pattern, flags=flags)
    return _re.sub(replacement, value, count)


def regex_findall(value, pattern, ignorecase=False, multiline=False):
    """Perform re.findall and return the list of matches"""

    value = to_text(value, errors="surrogate_or_strict", nonstring="simplerepr")

    flags = 0
    if ignorecase:
        flags |= re.I
    if multiline:
        flags |= re.M
    return str(re.findall(pattern, value, flags))


def regex_search(value, pattern, *args, **kwargs):
    """Perform re.search and return the list of matches or a backref"""

    value = to_text(value, errors="surrogate_or_strict", nonstring="simplerepr")

    groups = list()
    for arg in args:
        if arg.startswith("\\g"):
            match = re.match(r"\\g<(\S+)>", arg).group(1)
            groups.append(match)
        elif arg.startswith("\\"):
            match = int(re.match(r"\\(\d+)", arg).group(1))
            groups.append(match)
        else:
            raise Exception("Unknown argument")

    flags = 0
    if kwargs.get("ignorecase"):
        flags |= re.I
    if kwargs.get("multiline"):
        flags |= re.M

    match = re.search(pattern, value, flags)
    if match:
        if not groups:
            return str(match.group())
        else:
            items = list()
            for item in groups:
                items.append(match.group(item))
            return str(items)


def regex_escape(value, re_type="python"):
    value = to_text(value, errors="surrogate_or_strict", nonstring="simplerepr")
    # '''Escape all regular expressions special characters from STRING.'''
    if re_type == "python":
        return re.escape(value)
    if re_type == "posix_basic":
        # list of BRE special chars:
        # https://en.wikibooks.org/wiki/Regular_Expressions/POSIX_Basic_Regular_Expressions
        return regex_replace(value, r"([].[^$*\\])", r"\\\1")
    # TODO: implement posix_extended
    # It's similar to, but different from python regex, which is similar to,
    # but different from PCRE.  It's possible that re.escape would work here.
    # https://remram44.github.io/regex-cheatsheet/regex.html#programs
    elif re_type == "posix_extended":
        raise Exception(f"Regex type ({re_type}) not yet implemented")
    else:
        raise Exception(f"Invalid regex type ({re_type})")

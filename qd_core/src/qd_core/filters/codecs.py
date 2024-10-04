import re
from typing import Any, Iterable, Mapping, Tuple, Union
from urllib import parse as urllib_parse

import charset_normalizer
from jinja2.utils import url_quote
from requests.utils import get_encoding_from_headers


def get_encodings_from_content(content):
    """Returns encodings from given content string.

    :param content: bytestring to extract encodings from.
    """

    charset_re = re.compile(r'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
    pragma_re = re.compile(r'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
    xml_re = re.compile(r'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

    return charset_re.findall(content) + pragma_re.findall(content) + xml_re.findall(content)


def find_encoding(content, headers=None):
    # content is unicode
    if isinstance(content, str):
        return "utf-8"

    encoding = None

    # Try charset from content-type
    if headers:
        encoding = get_encoding_from_headers(headers)
        if encoding == "ISO-8859-1":
            encoding = None

    # Fallback to auto-detected encoding.
    if not encoding and charset_normalizer is not None:
        encoding = charset_normalizer.detect(content)["encoding"]

    # Try charset from content
    if not encoding:
        try:
            encoding = get_encodings_from_content(content)
            encoding = encoding and encoding[0] or None
        except Exception:
            if isinstance(content, bytes):
                return encoding or "utf-8"
            raise

    if encoding and encoding.lower() == "gb2312":
        encoding = "gb18030"

    return encoding or "latin_1"


def urlencode_with_encoding(
    value: Union[str, Mapping[str, Any], Iterable[Tuple[str, Any]]],
    encoding: str = "utf-8",
    for_qs: bool = False,
) -> str:
    """Quote data for use in a URL path or query using UTF-8.

    Basic wrapper around :func:`urllib.parse.quote` when given a
    string, or :func:`urllib.parse.urlencode` for a dict or iterable.

    :param value: Data to quote. A string will be quoted directly. A
        dict or iterable of ``(key, value)`` pairs will be joined as a
        query string.
    :param encoding: The encoding to use for quoted strings.
    :param for_qs: If ``True``, quote ``/`` as ``%2F``. If ``False``,
        leave slashes unquoted. Defaults to ``False``.

    When given a string, "/" is not quoted. HTTP servers treat "/" and
    "%2F" equivalently in paths. If you need quoted slashes, use the
    ``|replace("/", "%2F")`` filter.

    .. versionadded:: 2.7
    """
    if isinstance(value, str) or not isinstance(value, Iterable):
        return url_quote(value, charset=encoding, for_qs=for_qs)

    if isinstance(value, dict):
        items: Iterable[Tuple[str, Any]] = value.items()
    else:
        items = value  # type: ignore

    return "&".join(f"{url_quote(k, for_qs=True)}={url_quote(v, for_qs=True)}" for k, v in items)


def decode(content, headers=None):
    encoding = find_encoding(content, headers)
    if encoding == "unicode":
        return content

    return content.decode(encoding, "replace")


def quote_chinese(value, sep="", encoding="utf-8", decoding="utf-8"):
    if isinstance(value, str):
        return quote_chinese(value.encode(encoding))
    if isinstance(value, bytes):
        value = value.decode(decoding)
    res = [b if ord(b) < 128 else urllib_parse.quote(b) for b in value]
    if sep is not None:
        return sep.join(res)
    return res

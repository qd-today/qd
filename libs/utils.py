#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 22:00:27
# pylint: disable=broad-exception-raised

import base64
import datetime
import functools
import hashlib
import html
import ipaddress
import random
import re
import smtplib
import socket
import struct
import time
import uuid
from binascii import (a2b_base64, a2b_hex, a2b_qp, a2b_uu, b2a_base64, b2a_hex,
                      b2a_qp, b2a_uu, crc32, crc_hqx)
from email.mime.text import MIMEText
from hashlib import sha1
from typing import Any, Iterable, Mapping, Tuple, Union
from urllib import parse as urllib_parse

import charset_normalizer
import umsgpack  # type: ignore
from Crypto.Cipher import AES
from faker import Faker
from jinja2.filters import do_float, do_int
from jinja2.runtime import Undefined
from jinja2.utils import generate_lorem_ipsum, url_quote
from requests.utils import get_encoding_from_headers
from tornado import httpclient

import config
from libs.convert import to_bytes, to_native, to_text
from libs.log import Log
from libs.mcrypto import aes_decrypt, aes_encrypt, passlib_or_crypt

try:
    from hashlib import md5 as _md5  # pylint: disable=ungrouped-imports
except ImportError:
    # Assume we're running in FIPS mode here
    _md5 = None  # type: ignore

logger_util = Log('QD.Http.Util').getlogger()


def ip2int(addr):
    try:
        return struct.unpack("!I", socket.inet_aton(addr))[0]
    except Exception as e:
        logger_util.debug(e, exc_info=config.traceback_print)
        return int(ipaddress.ip_address(addr))


def ip2varbinary(addr: str, version: int):
    if version == 4:
        return socket.inet_aton(addr)
    if version == 6:
        return socket.inet_pton(socket.AF_INET6, addr)


def is_lan(ip):
    try:
        return ipaddress.ip_address(ip.strip()).is_private
    except Exception as e:
        logger_util.debug(e, exc_info=config.traceback_print)
        return False


def int2ip(addr):
    try:
        return socket.inet_ntoa(struct.pack("!I", addr))
    except Exception as e:
        logger_util.debug(e, exc_info=config.traceback_print)
        return str(ipaddress.ip_address(addr))


def varbinary2ip(addr: Union[bytes, int, str]):
    if isinstance(addr, int):
        return int2ip(addr)
    if isinstance(addr, str):
        addr = addr.encode('utf-8')
    if len(addr) == 4:
        return socket.inet_ntop(socket.AF_INET, addr)
    if len(addr) == 16:
        return socket.inet_ntop(socket.AF_INET6, addr)


def is_ip(addr=None):
    if addr:
        p = re.compile(r'''
         ((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # IPv4
         |::ffff:(0:)?((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # IPv4 mapped / translated addresses
         # |fe80:(:[0-9a-fA-F]{1,4}){0,4}(%\w+)? # IPv6 link-local
         |([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4} # IPv6 full
         |(([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})?::(([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})? # IPv6 with ::
         ''', re.VERBOSE)
        tmp = p.match(addr)
        if tmp and tmp[0] == addr:
            if ':' in tmp[0]:
                return 6
            else:
                return 4
        else:
            return 0
    return 0


def urlmatch(url):
    reobj = re.compile(r"""(?xi)\A
                ([a-z][a-z0-9+\-.]*://)?                            # Scheme
                ([a-z0-9\-._~%]+                                    # domain or IPv4 host
                |\[[a-z0-9\-._~%!$&'()*+,;=:]+\])                   # IPv6+ host
                (:[0-9]+)? """                                      # :port
                       )
    match = reobj.search(url)
    return match.group()


def url_match_with_limit(url):
    ip_middle_octet = r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))"
    ip_last_octet = r"(?:\.(?:0|[1-9]\d?|1\d\d|2[0-4]\d|25[0-5]))"

    reobj = re.compile(  # noqa: W605
        r"^"
        # protocol identifier
        r"(?:(?:https?|ftp)://)"
        # user:pass authentication
        r"(?:[-a-z\u00a1-\uffff0-9._~%!$&'()*+,;=:]+"
        r"(?::[-a-z0-9._~%!$&'()*+,;=:]*)?@)?"
        r"(?:"
        r"(?P<private_ip>"
        # IP address exclusion
        # private & local networks
        r"(?:(?:10|127)" + ip_middle_octet + r"{2}" + ip_last_octet + r")|"
        r"(?:(?:169\.254|192\.168)" + ip_middle_octet + ip_last_octet + r")|"
        r"(?:172\.(?:1[6-9]|2\d|3[0-1])" + ip_middle_octet + ip_last_octet + r"))"
        r"|"
        # private & local hosts
        r"(?P<private_host>"
        r"(?:localhost))"
        r"|"
        # IP address dotted notation octets
        # excludes loopback network 0.0.0.0
        # excludes reserved space >= 224.0.0.0
        # excludes network & broadcast addresses
        # (first & last IP address of each class)
        r"(?P<public_ip>"
        r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
        r"" + ip_middle_octet + r"{2}"
        r"" + ip_last_octet + r")"
        r"|"
        # IPv6 RegEx from https://stackoverflow.com/a/17871737
        r"\[("
        # 1:2:3:4:5:6:7:8
        r"([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|"
        # 1::                              1:2:3:4:5:6:7::
        r"([0-9a-fA-F]{1,4}:){1,7}:|"
        # 1::8             1:2:3:4:5:6::8  1:2:3:4:5:6::8
        r"([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|"
        # 1::7:8           1:2:3:4:5::7:8  1:2:3:4:5::8
        r"([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|"
        # 1::6:7:8         1:2:3:4::6:7:8  1:2:3:4::8
        r"([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|"
        # 1::5:6:7:8       1:2:3::5:6:7:8  1:2:3::8
        r"([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|"
        # 1::4:5:6:7:8     1:2::4:5:6:7:8  1:2::8
        r"([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|"
        # 1::3:4:5:6:7:8   1::3:4:5:6:7:8  1::8
        r"[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|"
        # ::2:3:4:5:6:7:8  ::2:3:4:5:6:7:8 ::8       ::
        r":((:[0-9a-fA-F]{1,4}){1,7}|:)|"
        # fe80::7:8%eth0   fe80::7:8%1
        # (link-local IPv6 addresses with zone index)
        r"fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|"
        r"::(ffff(:0{1,4}){0,1}:){0,1}"
        r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
        # ::255.255.255.255   ::ffff:255.255.255.255  ::ffff:0:255.255.255.255
        # (IPv4-mapped IPv6 addresses and IPv4-translated addresses)
        r"(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|"
        r"([0-9a-fA-F]{1,4}:){1,4}:"
        r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
        # 2001:db8:3:4::192.0.2.33  64:ff9b::192.0.2.33
        # (IPv4-Embedded IPv6 Address)
        r"(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])"
        r")\]|"
        # host name
        r"(?:(?:(?:xn--[-]{0,2})|[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]-?)*"
        r"[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]+)"
        # domain name
        r"(?:\.(?:(?:xn--[-]{0,2})|[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]-?)*"
        r"[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]+)*"
        # TLD identifier
        r"(?:\.(?:(?:xn--[-]{0,2}[a-z\u00a1-\uffff\U00010000-\U0010ffff0-9]{2,})|"
        r"[a-z\u00a1-\uffff\U00010000-\U0010ffff]{2,}))"
        r")"
        # port number
        r"(?::\d{2,5})?"
        # resource path
        r"(?:/[-a-z\u00a1-\uffff\U00010000-\U0010ffff0-9._~%!$&'()*+,;=:@/]*)?"
        # query string
        r"(?:\?\S*)?"
        # fragment
        r"(?:#\S*)?"
        r"$",
        re.UNICODE | re.IGNORECASE
    )

    match = reobj.search(url)
    if match:
        return match.group()
    return ''


def domain_match(domain):
    reobj = re.compile(
        r'^(?:[a-zA-Z0-9]'  # First character of the domain
        r'(?:[a-zA-Z0-9-_]{0,61}[A-Za-z0-9])?\.)'  # Sub domain + hostname
        r'+[A-Za-z0-9][A-Za-z0-9-_]{0,61}'  # First 61 characters of the gTLD
        r'[A-Za-z]$'  # Last character of the gTLD
    )

    match = reobj.search(domain)
    if match:
        return match.group()
    return ''


def func_cache(f):
    _cache = {}

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        key = umsgpack.packb((args, kwargs))
        if key not in _cache:
            _cache[key] = f(*args, **kwargs)
        return _cache[key]

    return wrapper


def method_cache(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        # pylint: disable=protected-access
        tmp = {}
        for k, v in kwargs.items():
            if k == 'sql_session':
                continue
            tmp[k] = v
        if not hasattr(self, '_cache'):
            self._cache = {}
        key = umsgpack.packb((args, tmp))
        if key not in self._cache:
            self._cache[key] = fn(self, *args, **kwargs)
        return self._cache[key]

    return wrapper

# full_format=True 的时候是具体时间，full_format=False就是几秒钟几分钟几小时时间格式----此处为模糊时间格式模式


def format_date(date, gmt_offset=time.timezone / 60, relative=True, shorter=False, full_format=True):
    """Formats the given date (which should be GMT).

    By default, we return a relative time (e.g., "2 minutes ago"). You
    can return an absolute date string with ``relative=False``.

    You can force a full format date ("July 10, 1980") with
    ``full_format=True``.

    This method is primarily intended for dates in the past.
    For dates in the future, we fall back to full format.
    """
    if not date:
        return '-'
    if isinstance(date, float) or isinstance(date, int):
        date = datetime.datetime.utcfromtimestamp(date)
    now = datetime.datetime.utcnow()
    local_date = date - datetime.timedelta(minutes=gmt_offset)
    local_now = now - datetime.timedelta(minutes=gmt_offset)
    local_yesterday = local_now - datetime.timedelta(hours=24)
    local_tomorrow = local_now + datetime.timedelta(hours=24)
    if date > now:
        later = "后"
        date, now = now, date
    else:
        later = "前"
    difference = now - date
    seconds = difference.seconds
    days = difference.days

    format = None
    if not full_format:
        if relative and days == 0:
            if seconds < 50:
                return f"{seconds} 秒" + later

            if seconds < 50 * 60:
                minutes = round(seconds / 60.0)
                return f"{minutes} 分钟" + later

            hours = round(seconds / (60.0 * 60))
            return f"{hours} 小时" + later

        if days == 0:
            format = "%(time)s"
        elif days == 1 and local_date.day == local_yesterday.day and \
                relative and later == '前':
            format = "昨天" if shorter else "昨天 %(time)s"
        elif days == 1 and local_date.day == local_tomorrow.day and \
                relative and later == '后':
            format = "明天" if shorter else "明天 %(time)s"
        # elif days < 5:
            # format = "%(weekday)s" if shorter else "%(weekday)s %(time)s"
        elif days < 334:  # 11mo, since confusing for same month last year
            format = "%(month_name)s-%(day)s" if shorter else \
                "%(month_name)s-%(day)s %(time)s"

    if format is None:
        format = "%(year)s-%(month_name)s-%(day)s" if shorter else \
            "%(year)s-%(month_name)s-%(day)s %(time)s"

    str_time = f"{local_date.hour:02d}:{local_date.minute:02d}:{local_date.second:02d}"

    return format % {
        "month_name": local_date.month,
        "weekday": local_date.weekday(),
        "day": str(local_date.day),
        "year": str(local_date.year),
        "time": str_time
    }


def utf8(value):
    if isinstance(value, str):
        return value.encode('utf8')
    return value


def conver2unicode(value, html_unescape=False):
    if not isinstance(value, str):
        try:
            value = value.decode()
        except Exception as e:
            logger_util.debug(e, exc_info=config.traceback_print)
            value = str(value)
    tmp = bytes(value, 'unicode_escape').decode('utf-8').replace(r'\u', r'\\u').replace(r'\\\u', r'\\u')
    tmp = bytes(tmp, 'utf-8').decode('unicode_escape')
    tmp = tmp.encode('utf-8').replace(b'\xc2\xa0', b'\xa0').decode('unicode_escape')
    if html_unescape:
        tmp = html.unescape(tmp)
    return tmp


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

    return "&".join(
        f"{url_quote(k, for_qs=True)}={url_quote(v, for_qs=True)}" for k, v in items
    )


def to_bool(value):
    ''' return a bool for the arg '''
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.lower()
    if value in ('yes', 'on', '1', 'true', 1):
        return True
    return False


async def send_mail(to, subject, text=None, html=None, shark=False, _from=f"QD提醒 <noreply@{config.domain}>"):
    if not config.mailgun_key:
        subtype = 'html' if html else 'plain'
        await _send_mail(to, subject, html or text or '', subtype)
        return

    httpclient.AsyncHTTPClient.configure('tornado.curl_httpclient.CurlAsyncHTTPClient')
    if shark:
        client = httpclient.AsyncHTTPClient()
    else:
        client = httpclient.HTTPClient()

    body = {
        'from': utf8(_from),
        'to': utf8(to),
        'subject': utf8(subject),
    }

    if text:
        body['text'] = utf8(text)
    elif html:
        body['html'] = utf8(html)
    else:
        raise Exception('need text or html')

    req = httpclient.HTTPRequest(
        method="POST",
        url=f"https://api.mailgun.net/v3/{config.mailgun_domain}/messages",
        auth_username="api",
        auth_password=config.mailgun_key,
        body=urllib_parse.urlencode(body)
    )
    res = await client.fetch(req)
    return res


async def _send_mail(to, subject, text=None, subtype='html'):
    if not config.mail_smtp:
        logger_util.info('no smtp')
        return
    msg = MIMEText(text, _subtype=subtype, _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = config.mail_from
    msg['To'] = to
    try:
        logger_util.info('send mail to %s', to)
        tls_established = False

        # Create SMTP connection according to the configuration
        if config.mail_starttls:  # use starttls
            s = smtplib.SMTP(config.mail_smtp, config.mail_port or 587)
            try:
                s.starttls()
                tls_established = True
            except smtplib.SMTPException as e:
                logger_util.error("smtp starttls failed: %s", e, exc_info=config.traceback_print)
        if not tls_established:
            if config.mail_ssl:
                s = smtplib.SMTP_SSL(config.mail_smtp, config.mail_port or 465)
            else:
                s = smtplib.SMTP(config.mail_smtp, config.mail_port or 25)

        try:
            # Only attempt login if user and password are set
            if config.mail_user and config.mail_password:
                s.login(config.mail_user, config.mail_password)
            s.sendmail(config.mail_from, to, msg.as_string())
        except smtplib.SMTPException as e:
            logger_util.error("smtp sendmail error: %s", e, exc_info=config.traceback_print)
        finally:
            # If sending fails, still close the connection
            s.quit()

    except Exception as e:
        logger_util.error('error occurred while sending mail: %s', e, exc_info=config.traceback_print)
    return


def get_encodings_from_content(content):
    """Returns encodings from given content string.

    :param content: bytestring to extract encodings from.
    """

    charset_re = re.compile(r'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
    pragma_re = re.compile(r'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
    xml_re = re.compile(r'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

    return (
        charset_re.findall(content)
        + pragma_re.findall(content)
        + xml_re.findall(content)
    )


def find_encoding(content, headers=None):
    # content is unicode
    if isinstance(content, str):
        return 'utf-8'

    encoding = None

    # Try charset from content-type
    if headers:
        encoding = get_encoding_from_headers(headers)
        if encoding == 'ISO-8859-1':
            encoding = None

    # Fallback to auto-detected encoding.
    if not encoding and charset_normalizer is not None:
        encoding = charset_normalizer.detect(content)['encoding']

    # Try charset from content
    if not encoding:
        try:
            encoding = get_encodings_from_content(content)
            encoding = encoding and encoding[0] or None
        except Exception as e:
            logger_util.debug(e, exc_info=config.traceback_print)
            if isinstance(content, bytes):
                return encoding or 'utf-8'

    if encoding and encoding.lower() == 'gb2312':
        encoding = 'gb18030'

    return encoding or 'latin_1'


def decode(content, headers=None):
    encoding = find_encoding(content, headers)
    if encoding == 'unicode':
        return content

    try:
        return content.decode(encoding, 'replace')
    except Exception as e:
        logger_util.error('utils.decode: %s', e, exc_info=config.traceback_print)
        return None


def quote_chinese(value, sep="", encoding="utf-8", decoding="utf-8"):
    if isinstance(value, str):
        return quote_chinese(value.encode(encoding))
    if isinstance(value, bytes):
        value = value.decode(decoding)
    res = [b if ord(b) < 128 else urllib_parse.quote(b) for b in value]
    if sep is not None:
        return sep.join(res)
    return res


def secure_hash_s(value, hash_func=sha1):
    ''' Return a secure hash hex digest of data. '''

    digest = hash_func()
    value = to_bytes(value, errors='surrogate_or_strict')
    digest.update(value)
    return digest.hexdigest()


def md5string(value):
    if _md5 is None:
        raise ValueError('MD5 not available. Possibly running in FIPS mode')
    return secure_hash_s(value, _md5)


def get_random(min_num, max_num, unit):
    random_num = random.uniform(min_num, max_num)
    # result = "%.{0}f".format(int(unit)) % random_num
    result = f"{random_num:.{int(unit)}f}"
    return result


def random_fliter(*args, **kwargs):
    try:
        result = get_random(*args, **kwargs)
    except Exception as e:
        logger_util.debug(e, exc_info=config.traceback_print)
        result = random.choice(*args, **kwargs)
    return result


def randomize_list(mylist, seed=None):
    try:
        mylist = list(mylist)
        if seed:
            r = random.Random(seed)
            r.shuffle(mylist)
        else:
            random.shuffle(mylist)
    except Exception as e:
        logger_util.debug(e, exc_info=config.traceback_print)
        raise e
    return mylist


def get_date_time(date=True, time=True, time_difference=0):
    if isinstance(date, str):
        date = int(date)
    if isinstance(time, str):
        time = int(time)
    if isinstance(time_difference, str):
        time_difference = int(time_difference)
    now_date = datetime.datetime.today() + datetime.timedelta(hours=time_difference)
    if date:
        if time:
            return str(now_date).split('.', maxsplit=1)[0]
        else:
            return str(now_date.date())
    elif time:
        return str(now_date.time()).split('.', maxsplit=1)[0]
    else:
        return ""


def strftime(string_format, second=None):
    ''' return a date string using string. See https://docs.python.org/3/library/time.html#time.strftime for format '''
    if second is not None:
        try:
            second = float(second)
        except Exception as e:
            raise Exception(f'Invalid value for epoch value ({second})') from e
    return time.strftime(string_format, time.localtime(second))


def regex_replace(value='', pattern='', replacement='', count=0, ignorecase=False, multiline=False):
    ''' Perform a `re.sub` returning a string '''

    value = to_text(value, errors='surrogate_or_strict', nonstring='simplerepr')

    flags = 0
    if ignorecase:
        flags |= re.I
    if multiline:
        flags |= re.M
    _re = re.compile(pattern, flags=flags)
    return _re.sub(replacement, value, count)


def regex_findall(value, pattern, ignorecase=False, multiline=False):
    ''' Perform re.findall and return the list of matches '''

    value = to_text(value, errors='surrogate_or_strict', nonstring='simplerepr')

    flags = 0
    if ignorecase:
        flags |= re.I
    if multiline:
        flags |= re.M
    return str(re.findall(pattern, value, flags))


def regex_search(value, pattern, *args, **kwargs):
    ''' Perform re.search and return the list of matches or a backref '''

    value = to_text(value, errors='surrogate_or_strict', nonstring='simplerepr')

    groups = list()
    for arg in args:
        if arg.startswith('\\g'):
            match = re.match(r'\\g<(\S+)>', arg).group(1)
            groups.append(match)
        elif arg.startswith('\\'):
            match = int(re.match(r'\\(\d+)', arg).group(1))
            groups.append(match)
        else:
            raise Exception('Unknown argument')

    flags = 0
    if kwargs.get('ignorecase'):
        flags |= re.I
    if kwargs.get('multiline'):
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


def ternary(value, true_val, false_val, none_val=None):
    '''  value ? true_val : false_val '''
    if (value is None or isinstance(value, Undefined)) and none_val is not None:
        return none_val
    elif bool(value):
        return true_val
    else:
        return false_val


def regex_escape(value, re_type='python'):
    value = to_text(value, errors='surrogate_or_strict', nonstring='simplerepr')
    # '''Escape all regular expressions special characters from STRING.'''
    if re_type == 'python':
        return re.escape(value)
    if re_type == 'posix_basic':
        # list of BRE special chars:
        # https://en.wikibooks.org/wiki/Regular_Expressions/POSIX_Basic_Regular_Expressions
        return regex_replace(value, r'([].[^$*\\])', r'\\\1')
    # TODO: implement posix_extended
    # It's similar to, but different from python regex, which is similar to,
    # but different from PCRE.  It's possible that re.escape would work here.
    # https://remram44.github.io/regex-cheatsheet/regex.html#programs
    elif re_type == 'posix_extended':
        raise Exception(f'Regex type ({re_type}) not yet implemented')
    else:
        raise Exception(f'Invalid regex type ({re_type})')


def timestamp(type='int'):
    if type == 'float':
        return time.time()
    return int(time.time())


def add(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i):
                result += float(i)
            else:
                return
        return f"{result:f}"
    return result


def sub(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i):
                result -= float(i)
            else:
                return
        return f"{result:f}"
    return result


def multiply(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i):
                result *= float(i)
            else:
                return
        return f"{result:f}"
    return result


def divide(*args):
    result = 0
    if args and is_num(args[0]):
        result = float(args[0])
        for i in args[1:]:
            if is_num(i) and float(i) != 0:
                result /= float(i)
            else:
                return
        return f"{result:f}"
    return result


def is_num(value: str = ''):
    value = str(value)
    if value.count('.') == 1:
        tmp = value.split('.')
        return tmp[0].lstrip('-').isdigit() and tmp[1].isdigit()
    else:
        return value.lstrip('-').isdigit()


def get_hash(value, hashtype='sha1'):
    try:
        h = hashlib.new(hashtype)
    except Exception as e:
        # hash is not supported?
        raise e

    h.update(to_bytes(value, errors='surrogate_or_strict'))
    return h.hexdigest()


def get_encrypted_password(password, hashtype='sha512', salt=None, salt_size=None, rounds=None, ident=None):
    passlib_mapping = {
        'md5': 'md5_crypt',
        'blowfish': 'bcrypt',
        'sha256': 'sha256_crypt',
        'sha512': 'sha512_crypt',
    }

    hashtype = passlib_mapping.get(hashtype, hashtype)
    return passlib_or_crypt(password, hashtype, salt=salt, salt_size=salt_size, rounds=rounds, ident=ident)


def to_uuid(value, namespace=uuid.NAMESPACE_URL):
    uuid_namespace = namespace
    if not isinstance(uuid_namespace, uuid.UUID):
        try:
            uuid_namespace = uuid.UUID(namespace)
        except (AttributeError, ValueError) as e:
            raise Exception(f"Invalid value '{to_native(namespace)}' for 'namespace': {to_native(e)}") from e
    # uuid.uuid5() requires bytes on Python 2 and bytes or text or Python 3
    return to_text(uuid.uuid5(uuid_namespace, to_native(value, errors='surrogate_or_strict')))


def mandatory(value, msg=None):
    ''' Make a variable mandatory '''
    if isinstance(value, Undefined):
        # pylint: disable=protected-access
        if value._undefined_name is not None:
            name = f"'{to_text(value._undefined_name)}' "
        else:
            name = ''

        if msg is not None:
            raise Exception(to_native(msg))
        else:
            raise Exception(f"Mandatory variable {name} not defined.")

    return value


def b64encode(value, encoding='utf-8'):
    return to_text(base64.b64encode(to_bytes(value, encoding=encoding, errors='surrogate_or_strict')))


def b64decode(value, encoding='utf-8'):
    return to_text(base64.b64decode(to_bytes(value, errors='surrogate_or_strict')), encoding=encoding)


def switch_mode(mode):
    mode = mode.upper()
    if mode == 'CBC':
        return AES.MODE_CBC
    elif mode == 'ECB':
        return AES.MODE_ECB
    elif mode == 'CFB':
        return AES.MODE_CFB
    elif mode == 'OFB':
        return AES.MODE_OFB
    elif mode == 'CTR':
        return AES.MODE_CTR
    elif mode == 'OPENPGP':
        return AES.MODE_OPENPGP
    elif mode == 'GCM':
        return AES.MODE_GCM
    elif mode == 'CCM':
        return AES.MODE_CCM
    elif mode == 'SIV':
        return AES.MODE_SIV
    elif mode == 'OCB':
        return AES.MODE_OCB
    elif mode == 'EAX':
        return AES.MODE_EAX
    else:
        raise Exception(f'Invalid AES mode: {mode}')


def _aes_encrypt(word: str, key: str, mode='CBC', iv: Union[str, bytes, None] = None, output_format='base64', padding=True, padding_style='pkcs7', no_packb=True):
    if key is None:
        raise Exception('key is required')
    if isinstance(iv, str):
        iv = iv.encode("utf-8")
    mode = switch_mode(mode)
    return aes_encrypt(word.encode("utf-8"), key.encode("utf-8"), mode=mode, iv=iv, output=output_format, padding=padding, padding_style=padding_style, no_packb=no_packb)


def _aes_decrypt(word: str, key: str, mode='CBC', iv: Union[str, bytes, None] = None, input_format='base64', padding=True, padding_style='pkcs7', no_packb=True):
    if key is None:
        raise Exception('key is required')
    if isinstance(iv, str):
        iv = iv.encode("utf-8")
    mode = switch_mode(mode)
    return aes_decrypt(word.encode("utf-8"), key.encode("utf-8"), mode=mode, iv=iv, input=input_format, padding=padding, padding_style=padding_style, no_packb=no_packb)


jinja_globals = {
    # types
    'int': do_int,
    'float': do_float,
    'bool': to_bool,
    'utf8': utf8,
    'unicode': conver2unicode,
    'urlencode': urlencode_with_encoding,
    'quote_chinese': quote_chinese,
    # binascii
    'b2a_hex': b2a_hex,
    'a2b_hex': a2b_hex,
    'b2a_uu': b2a_uu,
    'a2b_uu': a2b_uu,
    'b2a_base64': b2a_base64,
    'a2b_base64': a2b_base64,
    'b2a_qp': b2a_qp,
    'a2b_qp': a2b_qp,
    'crc_hqx': crc_hqx,
    'crc32': crc32,
    # format
    'format': format,
    # base64
    'b64decode': b64decode,
    'b64encode': b64encode,
    # uuid
    'to_uuid': to_uuid,
    # hash filters
    # md5 hex digest of string
    'md5': md5string,
    # sha1 hex digest of string
    'sha1': secure_hash_s,
    # generic hashing
    'password_hash': get_encrypted_password,
    'hash': get_hash,
    'aes_encrypt': _aes_encrypt,
    'aes_decrypt': _aes_decrypt,
    # time
    'timestamp': timestamp,
    'date_time': get_date_time,
    # Calculate
    'is_num': is_num,
    'add': add,
    'sub': sub,
    'multiply': multiply,
    'divide': divide,
    'Faker': Faker,
    # regex
    'regex_replace': regex_replace,
    'regex_escape': regex_escape,
    'regex_search': regex_search,
    'regex_findall': regex_findall,
    # ? : ;
    'ternary': ternary,
    # random stuff
    'random': random_fliter,
    'shuffle': randomize_list,
    # undefined
    'mandatory': mandatory,
    # debug
    'type_debug': lambda value: value.__class__.__name__,
}

jinja_inner_globals = {
    'dict': dict,
    'lipsum': generate_lorem_ipsum,
    'range': range,
}

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 22:00:27

import base64
import hashlib
import socket
import struct
import ipaddress
import uuid
import jinja2
from tornado import gen
from faker import Faker
import re
import urllib
import config
from tornado import httpclient

from libs.convert import to_text, to_bytes, to_native
from libs.mcrypto import passlib_or_crypt
from .log import Log

logger_Util = Log('qiandao.Http.Util').getlogger()
def ip2int(addr):
    try:
        return struct.unpack("!I", socket.inet_aton(addr))[0]
    except:
        return int(ipaddress.ip_address(addr))

def ip2varbinary(addr:str, version:int):
    if version == 4:
        return socket.inet_aton(addr)
    if version == 6:
        return socket.inet_pton(socket.AF_INET6,addr)
 
def is_lan(ip):
    try:
        return ipaddress.ip_address(ip.strip()).is_private
    except Exception as e:
        return False

def int2ip(addr):
    try:
        return socket.inet_ntoa(struct.pack("!I", addr))
    except:
        return str(ipaddress.ip_address(addr))

def varbinary2ip(addr:bytes or int or str):
    if isinstance(addr, int):
        return int2ip(addr)
    if isinstance(addr, str):
        addr = addr.encode('utf-8')
    if len(addr) == 4:
        return socket.inet_ntop(socket.AF_INET,addr)
    if len(addr) == 16:
        return socket.inet_ntop(socket.AF_INET6,addr)

def isIP(addr = None):
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

def getLocalScheme(scheme):
    if scheme in ['http','https']:
        if config.https:
            return 'https'
        else:
            return 'http'
    return scheme

import umsgpack
import functools

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
        if not hasattr(self, '_cache'):
            self._cache = dict()
        key = umsgpack.packb((args, kwargs))
        if key not in self._cache:
            self._cache[key] = fn(self, *args, **kwargs)
        return self._cache[key]

    return wrapper

import datetime

#full_format=True，的时候是具体时间，full_format=False就是几秒钟几分钟几小时时间格式----此处为模糊时间格式模式
def format_date(date, gmt_offset=-8*60, relative=True, shorter=False, full_format=True):
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
        later = u"后"
        date, now = now, date
    else:
        later = u"前"
    difference = now - date
    seconds = difference.seconds
    days = difference.days

    format = None
    if not full_format:
        if relative and days == 0:
            if seconds < 50:
                return u"%(seconds)d 秒" % {"seconds": seconds} + later

            if seconds < 50 * 60:
                minutes = round(seconds / 60.0)
                return u"%(minutes)d 分钟" % {"minutes": minutes} + later

            hours = round(seconds / (60.0 * 60))
            return u"%(hours)d 小时" % {"hours": hours} + later

        if days == 0:
            format = "%(time)s"
        elif days == 1 and local_date.day == local_yesterday.day and \
                relative and later == u'前':
            format = u"昨天" if shorter else u"昨天 %(time)s"
        elif days == 1 and local_date.day == local_tomorrow.day and \
                relative and later == u'后':
            format = u"明天" if shorter else u"明天 %(time)s"
        #elif days < 5:
            #format = "%(weekday)s" if shorter else "%(weekday)s %(time)s"
        elif days < 334:  # 11mo, since confusing for same month last year
            format = "%(month_name)s-%(day)s" if shorter else \
                "%(month_name)s-%(day)s %(time)s"

    if format is None:
        format = "%(year)s-%(month_name)s-%(day)s" if shorter else \
            "%(year)s-%(month_name)s-%(day)s %(time)s"

    str_time = "%d:%02d:%02d" % (local_date.hour, local_date.minute, local_date.second)

    return format % {
        "month_name": local_date.month,
        "weekday": local_date.weekday(),
        "day": str(local_date.day),
        "year": str(local_date.year),
        "time": str_time
    }

def utf8(string):
    if isinstance(string, str):
        return string.encode('utf8')
    return string

def conver2unicode(string):
    if not isinstance(string,str):
        try:
            string = string.decode()
        except :
            string =  str(string)
    tmp = bytes(string,'unicode_escape').decode('utf-8').replace(r'\u',r'\\u').replace(r'\\\u',r'\\u')
    tmp = bytes(tmp,'utf-8').decode('unicode_escape')
    return tmp.encode('utf-8').replace(b'\xc2\xa0',b'\xa0').decode('unicode_escape')

def to_bool(a):
    ''' return a bool for the arg '''
    if a is None or isinstance(a, bool):
        return a
    if isinstance(a, str):
        a = a.lower()
    if a in ('yes', 'on', '1', 'true', 1):
        return True
    return False

async def send_mail(to, subject, text=None, html=None, shark=False, _from=u"签到提醒 <noreply@{}>".format(config.mail_domain)):
    if not config.mailgun_key:
        subtype = 'html' if html else 'plain'
        _send_mail(to, subject, html or text or '', subtype)
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
        url="https://api.mailgun.net/v2/%s/messages" % config.mail_domain,
        auth_username="api",
        auth_password=config.mailgun_key,
        body=urllib.parse.urlencode(body)
    )
    res = await gen.convert_yielded(client.fetch(req))
    return res


import smtplib
from email.mime.text import MIMEText

def _send_mail(to, subject, text=None, subtype='html'):
    if not config.mail_smtp:
        logger_Util.info('no smtp')
        return
    msg = MIMEText(text, _subtype=subtype, _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = config.mail_from
    msg['To'] = to
    try:
        logger_Util.info('send mail to {}'.format(to))
        s = config.mail_ssl and smtplib.SMTP_SSL(config.mail_smtp) or smtplib.SMTP(config.mail_smtp)
        s.connect(config.mail_smtp)
        s.login(config.mail_user, config.mail_password)
        s.sendmail(config.mail_from, to, msg.as_string())
        s.close()
    except Exception as e:
        logger_Util.error('send mail error {}'.format(str(e)))
    return


import chardet
from requests.utils import get_encoding_from_headers, get_encodings_from_content


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
    if not encoding and chardet is not None:
        encoding = chardet.detect(content)['encoding']
    
    # Try charset from content
    if not encoding:
        try:
            encoding = get_encodings_from_content(content)
            encoding = encoding and encoding[0] or None
        except:
            if isinstance(content,bytes):
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
        logger_Util.error('utils.decode:',e)
        return None


def quote_chinese(url, encodeing="utf-8"):
    if isinstance(url, str):
        return quote_chinese(url.encode("utf-8"))
    if isinstance(url,bytes):
        url = url.decode()
    res = [b if ord(b) < 128 else urllib.parse.quote(b) for b in url]
    return "".join(res)


from hashlib import sha1
try:
    from hashlib import md5 as _md5
except ImportError:
    # Assume we're running in FIPS mode here
    _md5 = None

def secure_hash_s(data, hash_func=sha1):
    ''' Return a secure hash hex digest of data. '''

    digest = hash_func()
    data = to_bytes(data, errors='surrogate_or_strict')
    digest.update(data)
    return digest.hexdigest()

def md5string(data):
    if not _md5:
        raise ValueError('MD5 not available.  Possibly running in FIPS mode')
    return secure_hash_s(data, _md5)

import random
def get_random(min_num, max_num, unit):
    random_num = random.uniform(min_num, max_num)
    result = "%.{0}f".format(int(unit)) % random_num
    return result

def random_fliter(*args, **kwargs):
    try:
        result = get_random(*args, **kwargs)
    except:
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
    except Exception:
        raise
    return mylist

import datetime
def get_date_time(date=True, time=True, time_difference=0):
    if isinstance(date,str):
        date=int(date)
    if isinstance(time,str):
        time=int(time)
    if isinstance(time_difference,str):
        time_difference = int(time_difference)
    now_date = datetime.datetime.today() + datetime.timedelta(hours=time_difference)
    if date:
        if time:
            return str(now_date).split('.')[0]
        else:
            return str(now_date.date())
    elif time:
        return str(now_date.time()).split('.')[0]
    else:
        return ""

def strftime(string_format, second=None):
    ''' return a date string using string. See https://docs.python.org/3/library/time.html#time.strftime for format '''
    if second is not None:
        try:
            second = float(second)
        except Exception:
            raise Exception('Invalid value for epoch value (%s)' % second)
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
    if (value is None or isinstance(value, jinja2.Undefined)) and none_val is not None:
        return none_val
    elif bool(value):
        return true_val
    else:
        return false_val

def regex_escape(value, re_type='python'):
    value = to_text(value, errors='surrogate_or_strict', nonstring='simplerepr')
    '''Escape all regular expressions special characters from STRING.'''
    if re_type == 'python':
        return re.escape(value)
    elif re_type == 'posix_basic':
        # list of BRE special chars:
        # https://en.wikibooks.org/wiki/Regular_Expressions/POSIX_Basic_Regular_Expressions
        return regex_replace(value, r'([].[^$*\\])', r'\\\1')
    # TODO: implement posix_extended
    # It's similar to, but different from python regex, which is similar to,
    # but different from PCRE.  It's possible that re.escape would work here.
    # https://remram44.github.io/regex-cheatsheet/regex.html#programs
    elif re_type == 'posix_extended':
        raise Exception('Regex type (%s) not yet implemented' % re_type)
    else:
        raise Exception('Invalid regex type (%s)' % re_type)

import time
def timestamp(type='int'):
    if type=='float':
        return time.time()
    else:
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
        return '{:f}'.format(result)
    else:
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
        return '{:f}'.format(result)
    else:
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
        return '{:f}'.format(result)
    else:
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
        return '{:f}'.format(result)
    else:
        return result

def is_num(s:str=''):
    s = str(s)
    if s.count('.') ==1:
        tmp = s.split('.')
        return tmp[0].lstrip('-').isdigit() and tmp[1].isdigit()
    else:
        return s.lstrip('-').isdigit()

def get_hash(data, hashtype='sha1'):
    try:
        h = hashlib.new(hashtype)
    except Exception as e:
        # hash is not supported?
        raise Exception(e)

    h.update(to_bytes(data, errors='surrogate_or_strict'))
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

def to_uuid(string, namespace=uuid.NAMESPACE_URL):
    uuid_namespace = namespace
    if not isinstance(uuid_namespace, uuid.UUID):
        try:
            uuid_namespace = uuid.UUID(namespace)
        except (AttributeError, ValueError) as e:
            raise Exception("Invalid value '%s' for 'namespace': %s" % (to_native(namespace), to_native(e)))
    # uuid.uuid5() requires bytes on Python 2 and bytes or text or Python 3
    return to_text(uuid.uuid5(uuid_namespace, to_native(string, errors='surrogate_or_strict')))

def mandatory(a, msg=None):
    from jinja2.runtime import Undefined

    ''' Make a variable mandatory '''
    if isinstance(a, Undefined):
        if a._undefined_name is not None:
            name = "'%s' " % to_text(a._undefined_name)
        else:
            name = ''

        if msg is not None:
            raise Exception(to_native(msg))
        else:
            raise Exception("Mandatory variable %s not defined." % name)

    return a

def b64encode(string, encoding='utf-8'):
    return to_text(base64.b64encode(to_bytes(string, encoding=encoding, errors='surrogate_or_strict')))

def b64decode(string, encoding='utf-8'):
    return to_text(base64.b64decode(to_bytes(string, errors='surrogate_or_strict')), encoding=encoding)


jinja_globals = {
    # types
    'quote_chinese': quote_chinese,
    'bool': to_bool,
    'utf8': utf8,
    'unicode': conver2unicode,
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
    'type_debug': lambda o: o.__class__.__name__,
}

jinja_inner_globals = {
    'dict': dict,
    'lipsum': jinja2.utils.generate_lorem_ipsum,
    'range': range,
}
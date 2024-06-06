#!/usr/bin/env python
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 22:00:27
# pylint: disable=broad-exception-raised


from binascii import a2b_base64, a2b_hex, a2b_qp, a2b_uu, b2a_base64, b2a_hex, b2a_qp, b2a_uu, crc32, crc_hqx

from faker import Faker
from jinja2.filters import do_float, do_int
from jinja2.utils import generate_lorem_ipsum

from qd_core.filters.algorithm import b64decode, b64encode, get_hash, md5string, secure_hash_s, to_uuid
from qd_core.filters.calculate import add, divide, multiply, sub
from qd_core.filters.codecs import quote_chinese, urlencode_with_encoding
from qd_core.filters.convert import to_bool, to_bytes, to_unicode
from qd_core.filters.expression import ternary
from qd_core.filters.judge import is_num, mandatory
from qd_core.filters.mcrypto import _aes_decrypt, _aes_encrypt, get_encrypted_password
from qd_core.filters.random import random_fliter, randomize_list
from qd_core.filters.regex import regex_escape, regex_findall, regex_replace, regex_search
from qd_core.filters.time import get_date_time, timestamp

jinja_globals = {
    # types
    "int": do_int,
    "float": do_float,
    "bool": to_bool,
    "utf8": to_bytes,
    "unicode": to_unicode,
    "urlencode": urlencode_with_encoding,
    "quote_chinese": quote_chinese,
    # binascii
    "b2a_hex": b2a_hex,
    "a2b_hex": a2b_hex,
    "b2a_uu": b2a_uu,
    "a2b_uu": a2b_uu,
    "b2a_base64": b2a_base64,
    "a2b_base64": a2b_base64,
    "b2a_qp": b2a_qp,
    "a2b_qp": a2b_qp,
    "crc_hqx": crc_hqx,
    "crc32": crc32,
    # format
    "format": format,
    # base64
    "b64decode": b64decode,
    "b64encode": b64encode,
    # uuid
    "to_uuid": to_uuid,
    # hash filters
    # md5 hex digest of string
    "md5": md5string,
    # sha1 hex digest of string
    "sha1": secure_hash_s,
    # generic hashing
    "password_hash": get_encrypted_password,
    "hash": get_hash,
    "aes_encrypt": _aes_encrypt,
    "aes_decrypt": _aes_decrypt,
    # time
    "timestamp": timestamp,
    "date_time": get_date_time,
    # Calculate
    "is_num": is_num,
    "add": add,
    "sub": sub,
    "multiply": multiply,
    "divide": divide,
    "Faker": Faker,
    # regex
    "regex_replace": regex_replace,
    "regex_escape": regex_escape,
    "regex_search": regex_search,
    "regex_findall": regex_findall,
    # ? : ;
    "ternary": ternary,
    # random stuff
    "random": random_fliter,
    "shuffle": randomize_list,
    # undefined
    "mandatory": mandatory,
    # debug
    "type_debug": lambda value: value.__class__.__name__,
}

jinja_inner_globals = {
    "dict": dict,
    "lipsum": generate_lorem_ipsum,
    "range": range,
}

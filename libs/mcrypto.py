#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 21:01:31

import base64
import umsgpack
import config

from pbkdf2 import PBKDF2
from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Cipher import AES

random = Random.new()
def password_hash(word, salt=None, iterations=config.pbkdf2_iterations):
    if salt is None:
        salt = random.read(16)
    elif len(salt) > 16:
        _, salt, iterations = umsgpack.unpackb(salt)

    word = umsgpack.packb(word)

    rawhash = PBKDF2(word, salt, iterations).read(32)

    return umsgpack.packb([rawhash, salt, iterations])

def aes_encrypt(word, key=config.aes_key, iv=None):
    if iv is None:
        iv = random.read(16)

    word = umsgpack.packb(word)
    mod = len(word) % 16
    if mod != 0:
        word += b'\0' * (16-mod)

    aes = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = aes.encrypt(word)

    return umsgpack.packb([ciphertext, iv])

def aes_decrypt(word, key=config.aes_key, iv=None):
    if iv is None:
        word, iv = umsgpack.unpackb(word)
    else:
        raise Exception('no iv error')

    aes = AES.new(key, AES.MODE_CBC, iv)
    word = aes.decrypt(word)

    while word:
        try:
            return umsgpack.unpackb(word)
        except umsgpack.ExtraData:
            word = word[:-1]

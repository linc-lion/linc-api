#!/usr/bin/env python
# -*- coding: utf-8 -*-

from random import choice
from base64 import b64encode, b64decode
from string import printable, whitespace, letters, digits, ascii_letters
from itertools import izip, cycle

safechars = ''.join(sorted(set(printable) - set(whitespace)))

def gen_token(token_size=100):
    token = ''.join(choice(ascii_letters + digits) for x in range(token_size))
    return token

def mksecret(length=50):
    return ''.join(choice(safechars) for i in xrange(length))

def xor(w1, w2):
    return ''.join(chr(ord(c1)^ord(c2)) for c1, c2 in izip(w1, cycle(w2)))

def token_encode(word, secret):
    w = len(word)
    s = len(secret)
    base = "%.3d%s%s" % (w, secret[-1], word)
    b = len(base)
    if b < s:
        base += mksecret(s-b)
    return b64encode(xor(base, secret), '-_')

def token_decode(word, secret):
    base = xor(b64decode(word, '-_'), secret)
    return base[4:int(base[:3], 10)+4]

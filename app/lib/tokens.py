#!/usr/bin/env python
# -*- coding: utf-8 -*-

# LINC is an open source shared database and facial recognition
# system that allows for collaboration in wildlife monitoring.
# Copyright (C) 2016  Wildlifeguardians
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information or to contact visit linclion.org or email tech@linclion.org

from random import choice
from base64 import b64encode, b64decode
from string import printable, whitespace, digits, ascii_letters
from itertools import cycle

safechars = ''.join(sorted(set(printable) - set(whitespace)))

def gen_token(token_size=100):
    token = ''.join(choice(ascii_letters + digits) for x in range(token_size))
    return token

def mksecret(length=50):
    return ''.join(choice(safechars) for i in range(length))

def xor(w1, w2):
    return ''.join(chr(ord(c1)^ord(c2)) for c1, c2 in zip(w1, cycle(w2)))

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

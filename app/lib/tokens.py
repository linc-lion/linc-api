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
from logging import info

safechars = ''.join(sorted(set(printable) - set(whitespace)))

# Stupid XOR demo
from itertools import cycle

def gen_token(token_size=100):
    token = ''.join(choice(ascii_letters + digits) for x in range(token_size))
    return token

def mksecret(length=50):
    return ''.join(choice(safechars) for i in range(length))

def str_xor(word, secret):
    if isinstance(word,bytes):
        word = word.decode('utf-8')
    return ''.join(chr(ord(c)^ord(k)) for c,k in zip(word, cycle(secret)))

def token_encode(word, secret):
    altchars = bytearray('-_'.encode('utf-8'))
    encoded = str_xor(word, secret)
    return b64encode(bytearray(encoded.encode('utf-8')),altchars).decode('utf-8')

def token_decode(word, secret):
    altchars = bytearray('-_'.encode('utf-8'))
    decoded = str_xor(b64decode(word,altchars),secret)
    return decoded

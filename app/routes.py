#!/usr/bin/env python
# coding: utf-8

from handlers.base import VersionHandler
from handlers.error import ErrorHandler
from handlers.auth import AuthHandler


# Defining routes
url_patterns = [
    #(r"/auth/", AuthHandler),
    #(r"/auth/(?P<id>[a-zA-Z0-9_]+)/?$", AuthQueryHandler),
    #(r"/signal/", xHandler),
    #(r"/signal/(.*)", yHandler),
    (r"/version", VersionHandler)
]

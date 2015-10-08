#!/usr/bin/env python
# coding: utf-8

from handlers.base import VersionHandler
from handlers.error import ErrorHandler
from handlers.auth import AuthHandler
import sys
sys.path.append("../db")
sys.path.append("../")
from db.import2mongodb import ImportHandler


# Defining routes
url_patterns = [
    #(r"/auth/", AuthHandler),
    #(r"/auth/(?P<id>[a-zA-Z0-9_]+)/?$", AuthQueryHandler),
    #(r"/signal/", xHandler),
    #(r"/signal/(.*)", yHandler),
    (r"/version", VersionHandler),
    # The handler above will be used only for import data from pg in development phase
    (r"/import", ImportHandler)
]

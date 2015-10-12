#!/usr/bin/env python
# coding: utf-8

import os
import site
import sys
import tornado
import tornado.template
from tornado.options import define, options
from handlers.error import ErrorHandler
from tornado.ioloop import IOLoop
from motorengine.connection import connect

# Adjusting path for the app

# make filepaths relative to settings.
ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

# save original Python path
old_sys_path = list(sys.path)

# add local packages directories to Python's site-packages path
site.addsitedir(path('handlers'))  # Request handlers

# add local dependencies
if os.path.exists(path('lib')):
    for directory in os.listdir(path('lib')):
        full_path = path('lib/%s' % directory)
        if os.path.isdir(full_path):
            site.addsitedir(full_path)

# move the new items to the front of sys.path
new_sys_path = []
for item in list(sys.path):
    if item not in old_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

define("port",default=5000,type=int,help=("Server port"))
define("config",default=None,help=("Tornado configuration file"))
define('debug',default=True,type=bool,help=("Turn on autoreload, log to stderr only"))

tornado.options.parse_command_line()

# Keys can be generated with hashlib and must be changed before deploy
# Example:
#
# import hashlib
# hashlib.sha256('sample').hexdigest()

io_loop = IOLoop.instance()
db = connect("linc-api-lions", host="localhost", port=27017, io_loop=io_loop)

# API settings
api = {}
api['debug'] = options.debug
api['cookie_secret'] = 'fc0bd5422998a1620c292bbcd8369d7484d1d4e6e78ce1dde1e19d4321f64f17'
api['xsrf_cookies'] = False
api['app_path'] = os.path.dirname(os.path.realpath(__file__))
api['default_handler_class'] = ErrorHandler
api['default_handler_args'] = dict(status_code=404)
api['version'] = 'api version 0.1'
api['db'] = db
api['animal'] = 'lion'
api['animals'] = 'lions'

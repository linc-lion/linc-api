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
ROOT = os.path.dirname(os.path.realpath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

# save original Python path
old_sys_path = list(sys.path)

# add local packages directories to Python's site-packages path
site.addsitedir(path('handlers'))  # Request handlers
site.addsitedir(ROOT)
site.addsitedir(ROOT+'/models')
site.addsitedir(ROOT+'/handlers')

# add local dependencies
if os.path.exists(path('lib')):
    for directory in os.listdir(path('lib')):
        full_path = path('lib/%s' % directory)
        if os.path.isdir(full_path):
            site.addsitedir(full_path)

# move the new items to the front of sys.path
new_sys_path = [ROOT,ROOT+'/handlers',ROOT+'/models']
for item in list(sys.path):
    if item not in old_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

# database directory
site.addsitedir("../db")

define("port",default=5000,type=int,help=("Server port"))
define("config",default=None,help=("Tornado configuration file"))
define('debug',default=True,type=bool,help=("Turn on autoreload, log to stderr only"))

tornado.options.parse_command_line()

# Keys can be generated with hashlib and must be changed before deploy
# Example:
#
# import hashlib
# hashlib.sha256('sample').hexdigest()


# API settings
api = {}
api['debug'] = options.debug
api['cookie_secret'] = 'fc0bd5422998a1620c292bbcd8369d7484d1d4e6e78ce1dde1e19d4321f64f17'
api['xsrf_cookies'] = False
api['app_path'] = os.path.dirname(os.path.realpath(__file__))
api['default_handler_class'] = ErrorHandler
api['default_handler_args'] = dict(status_code=404)
api['version'] = 'api version 0.1'

# Setting about deploy and CV Server
api['animal'] = 'lion'
api['animals'] = 'lions'

# MongoDB Connection
io_loop = IOLoop.instance()
URI = os.environ.get("MONGOLAB_URI","local")
if URI == "local":
    db = connect("linc-api-"+api['animals'], host="localhost", port=27017,io_loop=io_loop)
else:
    dbname = URI.split("://")[1].split(":")[0]
    db = connect(db=dbname,alias=URI,io_loop=io_loop)
api['db'] = db

api['CVSERVER_URL_IDENTIFICATION'] = 'https://linc.semantic.md/identifications'
api['CVSERVER_URL_RESULTS'] = 'https://linc.semantic.md/results/'
api['CV_USERNAME'] = 'c0a5531d33b987dc76af6298c3f6765a34793ba5'
api['CV_PASSWORD'] = 'cbfdac6008f9cab4083784cbd1874f76618d2a97'

api['S3_URL'] = 'http://linc-production.s3.amazonaws.com/'

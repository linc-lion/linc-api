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
from motor import MotorClient as connect

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

# API settings
api = {}
api['debug'] = options.debug
api['xsrf_cookies'] = False
api['app_path'] = os.path.dirname(os.path.realpath(__file__))
api['default_handler_class'] = ErrorHandler
api['default_handler_args'] = dict(status_code=404)
api['version'] = 'api version 0.1'

# Token security
api['attempts'] = dict()
api['wait_list'] = dict()
api['tokens'] = dict()

# Setting about deploy and CV Server
api['animal'] = 'lion'
api['animals'] = 'lions'

# MongoDB Connection
URI = os.environ.get("MONGOLAB_URI","local")
if URI == "local":
    conn = connect("mongodb://localhost:27017")
    db = conn['linc-api-'+api['animals']]
else:
    dbname = URI.split("://")[1].split(":")[0]
    conn = connect(URI)
    db = conn[dbname]

api['db'] = db

from lib.tokens import gen_token,mksecret
api['cookie_secret'] = os.environ.get('COOKIE_SECRET',gen_token(50))
api['token_secret'] = os.environ.get('TOKEN_SECRET',mksecret(50))

api['CVSERVER_URL_IDENTIFICATION'] = os.environ.get('CVSERVER_URL_IDENTIFICATION','')
api['CVSERVER_URL_RESULTS'] = os.environ.get('CVSERVER_URL_RESULTS','')
api['CV_USERNAME'] = os.environ.get('CV_USERNAME','')
api['CV_PASSWORD'] = os.environ.get('CV_PASSWORD','')

api['S3_BUCKET'] = os.environ.get('S3_BUCKET','')
api['S3_FOLDER'] = 'linc-api-'+api['animals']
api['S3_URL'] = os.environ.get('S3_URL','')+api['S3_FOLDER']+'/'

api['S3_ACCESS_KEY'] = os.environ.get('S3_ACCESS_KEY','')
api['S3_SECRET_KEY'] = os.environ.get('S3_SECRET_KEY','')

api['url'] = os.environ.get('API_URL','')

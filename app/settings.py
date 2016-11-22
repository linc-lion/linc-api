#!/usr/bin/env python
# coding: utf-8

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

import os
import site
import sys
import tornado
import tornado.template
from tornado.options import define, options
from handlers.error import ErrorHandler
from tornado.ioloop import IOLoop
from motor import MotorClient as connect
from lib.check_cv import checkresults
from lib.check_s3 import checkS3
from apscheduler.schedulers.tornado import TornadoScheduler
from pymongo import MongoClient
from logging import info

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

define("port",default=5050,type=int,help=("Server port"))
define("config",default=None,help=("Tornado configuration file"))
define('debug',default=True,type=bool,help=("Turn on autoreload, log to stderr only"))
tornado.options.parse_command_line()

appdir = os.path.dirname(os.path.realpath(__file__))

# API settings
api = {}
api['debug'] = options.debug
api['xsrf_cookies'] = False
api['app_path'] = appdir
api['version'] = 'api version v1.0.0 - 20160117'
api['template_path'] = os.path.join(appdir,"templates")
api['static_path'] = os.path.join(appdir, "static")

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
    pm = MongoClient("mongodb://localhost:27017")
    db = conn['linc-api-'+api['animals']]
    sdb = pm['linc-api-'+api['animals']]
else:
    dbname = URI.split("://")[1].split(":")[0]
    conn = connect(URI)
    pm = MongoClient(URI)
    db = conn[dbname]
    sdb = pm[dbname]

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

api['EMAIL_FROM'] = os.environ.get('EMAIL_FROM','linclionproject@gmail.com')
api['SMTP_SERVER'] = os.environ.get('SMTP_SERVER','email-smtp.us-east-1.amazonaws.com')
api['SMTP_USERNAME'] = os.environ.get('SMTP_USERNAME','')
api['SMTP_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
api['SMPT_PORT'] = os.environ.get('SMTP_PORT','587')

api['url'] = os.environ.get('API_URL','')
api['scheduler'] = TornadoScheduler()
api['scheduler'].start()
# Check CV Server results - every 30 seconds
api['scheduler'].add_job(checkresults, 'interval', seconds=30, args=[sdb,api])
# Delete files in S3
api['scheduler'].add_job(checkS3, 'interval', hours=4, args=[sdb,api])

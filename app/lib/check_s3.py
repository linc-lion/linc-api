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

from tornado.httpclient import AsyncHTTPClient,HTTPRequest,HTTPError
from tornado import gen
from tornado.web import asynchronous
from tornado.escape import json_decode
from logging import info
from datetime import datetime
from json import dumps,loads
import boto
from boto.s3.connection import Bucket, Key

@gen.coroutine
def checkS3(db,api):
    # Get list for DELETE
    dellist = db.dellist.find()
    dellist = [x for x in dellist]
    if len(dellist) > 0:
        # Connect to S3
        S3_ACCESS_KEY = api['S3_ACCESS_KEY']
        S3_SECRET_KEY = api['S3_SECRET_KEY']
        S3_BUCKET = api['S3_BUCKET']
        try:
            conn = boto.connect_s3(S3_ACCESS_KEY,S3_SECRET_KEY,is_secure=False,calling_format=OrdinaryCallingFormat())
            bucket = Bucket(conn, S3_BUCKET)
            info('\nConnected to S3')
        except:
            info('\nFail to connect to S3')
            return
        for rmlist in dellist:
            if rmlist['list']:
                info('Removing files from: '+str(rmlist['ts']))
                reqs = list()
                try:
                    alldeleted = True
                    for key in rmlist['list']:
                        info(str(key))
                        info(str(S3_BUCKET))
                        k = Key(bucket = bucket, name=key)
                        if k.exists():
                            k.delete()
                        if k.exists():
                            alldeleted = False
                    if alldeleted:
                        res = db.dellist.remove({'_id':rmlist['_id']})
                except:
                    info('Error in the deletion of images')

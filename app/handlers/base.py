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

from tornado.web import RequestHandler,asynchronous
from tornado.gen import engine,coroutine
from tornado import web
from tornado.escape import utf8
import string,os
from datetime import date
from logging import info
import bcrypt
from json import load,loads,dumps,dump
from lib.tokens import token_decode,gen_token
from os import remove
from tornado.httpclient import AsyncHTTPClient,HTTPRequest,HTTPError
from tornado.httputil import HTTPHeaders
from tinys3 import Connection as s3con

class BaseHandler(RequestHandler):
    """A class to collect common handler methods - all other handlers should
    inherit this one.
    """
    def initS3(self):
        S3_ACCESS_KEY = self.settings['S3_ACCESS_KEY']
        S3_SECRET_KEY = self.settings['S3_SECRET_KEY']
        S3_BUCKET = self.settings['S3_BUCKET']
        conn = None
        try:
            conn = s3con(S3_ACCESS_KEY,S3_SECRET_KEY,default_bucket=S3_BUCKET)
        except:
            print('\n\nFail to connect to S3')
        return conn

    def prepare(self):
        #self.auth_check()
        self.input_data = dict()
        if self.request.method in ['POST','PUT'] and \
           "Content-Type" in self.request.headers.keys() and \
           self.request.headers["Content-Type"].startswith("application/json"):
            try:
                if self.request.body:
                    self.input_data = loads(self.request.body.decode("utf-8"))
                for k,v in self.request.arguments.items():
                    if str(k) != str(self.request.body.decode("utf-8")):
                        self.input_data[k] = v[0].decode("utf-8")
            except ValueError:
                self.dropError(400,'Fail to parse input data.')

    def get_current_user(self):
        max_days_valid=10
        # check for https comunication
        using_ssl = (self.request.headers.get('X-Scheme', 'http') == 'https')
        if not using_ssl:
            info('Not using SSL')
        else:
            info('Using SSL')
        # get the token for authentication
        token = self.request.headers.get("Linc-Api-AuthToken")
        res = None
        if token:
            # Decode to test
            try:
                token = token_decode(token,self.settings['token_secret'])
                # Check token and it will validate if it ir younger that 10 days
                vtoken = web.decode_signed_value(self.settings["cookie_secret"],'authtoken',token,max_age_days=max_days_valid)
            except:
                vtoken = None
            if vtoken:
                dtoken = loads(vtoken)
                # Check if the Tornado signed_value cookie functions
                if dtoken['username'] in self.settings['tokens'].keys() and \
                    self.settings['tokens'][dtoken['username']]['token'] == token:
                    res = dtoken
            else:
                # Validation error
                self.token_passed_but_invalid = True
        return res

    @asynchronous
    @engine
    def new_iid(self,collection,callback=None):
        iid = yield self.settings['db'].counters.find_and_modify(query={'_id':collection}, update={'$inc' : {'next':1}}, new=True, upsert=True)
        callback(int(iid['next']))

    def parseInput(self,objmodel):
        valid_fields = objmodel._fields.keys()
        newobj = dict()
        for k,v in self.input_data.items():
            if k in valid_fields:
                newobj[k] = v
        return newobj

    def switch_iid(self,obj):
        obj['id'] = obj['iid']
        del obj['iid']

    def setSuccess(self,code=200,message="",data=None):
        output_response = {'status':'success','message':message}
        if data:
            output_response['data'] = loads(self.json_encode(data))
        self.set_status(code)
        self.finish(output_response)

    def dropError(self,code=400,message=""):
        self.set_status(code)
        self.finish({'status':'error', 'message':message})

    def json_encode(self,value):
        return dumps(value,default=str).replace("</", "<\\/")

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

    def age(self,born):
        if born:
            today = date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        else:
            return "-"

    def encryptPassword(self,password):
        return bcrypt.hashpw(utf8(password), bcrypt.gensalt())

    def checkPassword(self,password,hashed):
        return bcrypt.hashpw(utf8(password), utf8(hashed)) == utf8(hashed)

    def imgurl(self,urlpath,imgtype='thumbnail'):
        # type can be: full,medium,thumbnail and icon
        url = self.settings['S3_URL'] + urlpath
        if imgtype == 'thumbnail':
            url = url + '_thumbnail.jpg'
        elif imgtype == 'full':
            url = url + '_full.jpg'
        elif imgtype == 'icon':
            url = url + '_icon.jpg'
        else:
        #imgtype == 'medium':
            url = url + '_medium.jpg'
        return url

    def remove_file(self,fname):
        try:
            remove(fname)
        except:
            pass

    def sanitizestr(self,strs):
        txt = "%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c for c in strs if c in txt)

    @asynchronous
    @engine
    def api(self,url,method,body=None,headers=None,auth_username=None,auth_password=None,callback=None):
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        http_client = AsyncHTTPClient()
        dictheaders = {"content-type": "application/json"}
        if headers:
            for k,v in headers.iteritems():
                dictheaders[k] = v
        h = HTTPHeaders(dictheaders)
        params={
            'headers' : h,
            'url' : url,
            'method' : method,
            'request_timeout': 720,
            'validate_cert' : False}
        if method in ['POST','PUT']:
            params['body'] = body
        if auth_username:
            params['auth_username'] = auth_username
            params['auth_password'] = auth_password
        request = HTTPRequest(**params)
        try:
            response = yield http_client.fetch(request)
        except HTTPError as e:
            info('HTTTP error returned... ')
            info("Code: "+str(e.code))
            info("Message: "+str(e.message))
            if e.response:
                info('URL: '+str(e.response.effective_url))
                info('Reason: '+str(e.response.reason))
                info('Body: '+str(e.response.body))
                response = e.response
            else:
                responde = e
        except Exception as e:
            # Other errors are possible, such as IOError.
            print("Other Errors: " + str(e))
            response = e
        callback(response)

class VersionHandler(BaseHandler):
    def get(self):
        self.setSuccess(200,self.settings['version']+' - animal defined: '+self.settings['animal'])

class DocHandler(BaseHandler):
    def get(self):
        self.set_header('Content-Type','text/html; charset=UTF-8')
        self.render('documentation.html')

class LogInfoHandler(BaseHandler):
    def put(self):
        output = [ self.settings['attempts'],self.settings['wait_list'],self.settings['tokens']]
        self.setSuccess(200,'log info',output)

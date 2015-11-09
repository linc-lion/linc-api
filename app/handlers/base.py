#!/usr/bin/env python
# -*- coding: utf-8 -*-

from json import load,loads,dumps,dump
from tornado.web import RequestHandler,asynchronous
from tornado.gen import engine,coroutine
from tornado.escape import utf8
import string,os
from datetime import date
import hashlib

class BaseHandler(RequestHandler):
    """A class to collect common handler methods - all other handlers should
    inherit this one.
    """
    def prepare(self):
        #self.auth_check()
        self.input_data = dict()
        if self.request.method in ['POST','PUT'] and \
           self.request.headers["Content-Type"].startswith("application/json"):
            try:
                if self.request.body:
                    self.input_data = loads(self.request.body.decode("utf-8"))
                for k,v in self.request.arguments.items():
                    if str(k) != str(self.request.body.decode("utf-8")):
                        self.input_data[k] = v[0].decode("utf-8")
            except ValueError:
                self.dropError(400,'Fail to parse input data.')

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

    def auth_check(self):
        # This method depends of the authentication method defined for the project
        pass
        #key = self.get_argument('auth_key',None)
        #if key != self.settings['auth_key']:
        #    self.authfail()



    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

    def age(self,born):
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def encryptPassword(self,pattern):
        return hashlib.sha256(utf8(pattern)).hexdigest()



    def sanitizestr(self,strs):
        txt = "%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c for c in strs if c in txt)

    # http status code returned will be rechecked soon
    def authfail(self):
        self.set_status(401)
        self.write({'status':'fail','message':'authentication failed'})
        self.finish()

    def data_exists(self,message=""):
        self.set_status(409)
        self.write({"status":"fail", "message":message})
        self.finish()

    def not_found(self,message=""):
         self.set_status(404)
         self.write({'status':'fail','message':message})
         self.finish()

class VersionHandler(BaseHandler):
    def get(self):
        self.setSuccess(200,self.settings['version']+' - animal defined: '+self.settings['animal'])

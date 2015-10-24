#!/usr/bin/env python
# -*- coding: utf-8 -*-

from json import load,loads,dumps,dump
from tornado.web import RequestHandler,asynchronous
from tornado.gen import engine,coroutine
import string,os
from datetime import date

class BaseHandler(RequestHandler):
    """A class to collect common handler methods - all other handlers should
    inherit this one.
    """

    def prepare(self):
        self.input_data = dict()
        if self.request.headers["Content-Type"].startswith("application/json"):
            try:
                if self.request.body:
                    self.input_data = json_decode(self.request.body.decode("utf-8"))
                for k,v in self.request.arguments.items():
                    if str(k) != str(self.request.body.decode("utf-8")):
                        self.input_data[k] = v[0].decode("utf-8")
                self.input_data = recursive_unicode(self.input_data)
            except ValueError:
                self.send_error(400, reason='Invalid input data.')

    @asynchronous
    @engine
    def new_iid(self,collection,callback=None):
        iid = yield self.settings['db'].counters.find_and_modify(query={'_id':collection}, update={'$inc' : {'next':1}}, new=True, upsert=True)
        callback(iid['next'])

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

    def sanitizestr(self,strs):
        txt = "%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c for c in strs if c in txt)

    def json_encode(self,value):
        return dumps(value,default=str).replace("</", "<\\/")

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

    def write_error(self, status_code, **kwargs):
        self.write({'status':'error','message':'fail to execute request','code':str(status_code)})
        self.finish()

    def auth_check(self):
        # This method depends of the authentication method defined for the project
        pass
        #key = self.get_argument('auth_key',None)
        #if key != self.settings['auth_key']:
        #    self.authfail()

    def dropError(self,code=400,message=""):
        self.set_status(code)
        self.write({'status':'error', 'message':message})
        self.finish()

    def prepare(self):
        self.auth_check()
        self.input_data = dict()
        try:
            if self.request.body:
                self.input_data = loads(self.request.body.decode("utf-8"))
            for k,v in self.request.arguments.items():
                if str(k) != str(self.request.body.decode("utf-8")):
                    self.input_data[k] = v[0].decode("utf-8")
        except ValueError:
            self.dropError(400,'Failure parsing input data.')

    # http status code returned will be rechecked soon
    def authfail(self):
        self.set_status(401)
        self.write({'status':'fail','message':'authentication failed'})
        self.finish()

    def success(self,message="",data=None,create=False):
        if create:
            self.set_status(201)
        else:
            self.set_status(200)
        output_response = {'status':'success','message':message}
        if data:
            output_response['data'] = data
        self.write(output_response)
        self.finish()

    def data_exists(self,message=""):
        self.set_status(409)
        self.write({"status":"fail", "message":message})
        self.finish()



    def not_found(self,message=""):
         self.set_status(404)
         self.write({'status':'fail','message':message})
         self.finish()

    def age(self,born):
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class VersionHandler(BaseHandler):
    def get(self):
        self.success(message=self.settings['version']+' - animal defined: '+self.settings['animal'])

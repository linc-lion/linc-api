#!/usr/bin/env python
# coding: utf-8

from tornado.web import asynchronous
from tornado.gen import engine
from handlers.base import BaseHandler

class AuthHandler(BaseHandler):
    @asynchronous
    @engine
    def get(self,query=''):
        pass
        #result = yield Task(self.read_data,**params)
        #self.success(message="users allowed",data=result)


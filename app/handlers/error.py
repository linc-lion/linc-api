#!/usr/bin/env python
# coding: utf-8

from handlers.base import BaseHandler
from tornado.web import asynchronous,ErrorHandler as EHandler

class ErrorHandler(EHandler, BaseHandler):
    """ Error handling """
    def get(self):
        self.reqresp(self)

    def post(self):
        self.reqresp(self)

    def put(self):
        self.reqresp(self)

    def delete(seld):
        self.reqresp(self)

    def reqresp(self):
        self.write({'status':'error','message':'resource can not be accessed','code':str(self.status_code)})

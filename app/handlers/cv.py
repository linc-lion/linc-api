#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine
from handlers.base import BaseHandler
from models.cv import CVRequest,CVResult

class CVRequestsHandler(BaseHandler):
    """A class that handles requests about CV requests
    """
    @asynchronous
    @coroutine
    def get(self):
        objs = yield CVRequest.objects.find_all()
        objs = [x.to_son() for x in objs]
        self.finish(self.json_encode(objs))

class CVResultsHandler(BaseHandler):
    """A class that handles requests about CV results
    """
    @asynchronous
    @coroutine
    def get(self):
        objs = yield CVResult.objects.find_all()
        #objs = [x.to_son() for x in objs]
        self.finish(self.json_encode(objs))

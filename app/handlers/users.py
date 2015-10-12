#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine
from handlers.base import BaseHandler
from models.user import User

class UsersHandler(BaseHandler):
    """A class that handles requests about users informartion
    """
    @asynchronous
    @coroutine
    def get(self):
        objs = yield User.objects.find_all()
        objs = [x.to_son() for x in objs]
        for x in objs:
            del x['encrypted_password']
        self.finish(self.json_encode(objs))

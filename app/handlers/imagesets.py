#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine
from handlers.base import BaseHandler
from models.imageset import ImageSet,Image

class ImageSetsHandler(BaseHandler):
    """A class that handles requests about image sets informartion
    """
    @asynchronous
    @coroutine
    def get(self):
        objs = yield ImageSet.objects.find_all()
        objs = [x.to_son() for x in objs]
        self.finish(self.json_encode(objs))

class ImagesHandler(BaseHandler):
    """A class that handles requests about images
    """
    @asynchronous
    @coroutine
    def get(self):
        objs = yield Image.objects.find_all()
        objs = [x.to_son() for x in objs]
        self.finish(self.json_encode(objs))

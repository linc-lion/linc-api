#!/usr/bin/env python
# coding: utf-8

# This file starts the web server and it don't need to be edited
# All settings and configurations are included in the settings.py file
# API routes must be defined in the routes.py file

import tornado
import tornado.web
import tornado.httpserver
import tornado.ioloop
from tornado.options import options
import logging
from sys import stdout
from settings import api as settings
from routes import url_patterns

logging.basicConfig(
    stream=stdout,
    level=logging.DEBUG,
    format='"%(asctime)s %(levelname)8s %(name)s - %(message)s"',
    datefmt='%H:%M:%S'
)

url_routes = url_patterns(settings['animals'])

# Tornado application
class Application(tornado.web.Application):
    def __init__(self):
        tornado.web.Application.__init__(self, url_routes, **settings)

# Run server
def main():
    app = Application()
    print('API handlers:')
    for h in url_routes:
        print(h)
    httpserver = tornado.httpserver.HTTPServer(app)
    httpserver.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

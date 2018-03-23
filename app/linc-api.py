#!/usr/bin/env python
# coding: utf-8

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

# This file starts the web server and it don't need to be edited
# All settings and configurations are included in the settings.py file
# API routes must be defined in the routes.py file

import tornado
import tornado.web
import tornado.httpserver
import tornado.ioloop
from tornado.options import options
import logging
from settings import api as settings
from routes import url_patterns
import os

logger = logging.getLogger()
url_routes = url_patterns(settings['animals'])


# Tornado application
class Application(tornado.web.Application):
    def __init__(self):
        tornado.web.Application.__init__(self, url_routes, **settings)


# Run server
def main():
    app = Application()

    if (len(logger.handlers) > 0):
        formatter = logging.Formatter("[%(levelname).1s %(asctime)s %(module)s:%(lineno)s] %(message)s", datefmt='%y%m%d %H:%M:%S')
        logger.handlers[0].setFormatter(formatter)
    if options.debug:
        logging.info('== Tornado in DEBUG mode ==============================')
        for key, cfg in settings.items():
            logging.info(key + ' = ' + str(cfg))
        logging.info('=======================================================')

    logging.info('API handlers:')
    for h in url_routes:
        logging.info(h)
    httpserver = tornado.httpserver.HTTPServer(app)
    httpserver.listen(os.environ.get("PORT", options.port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

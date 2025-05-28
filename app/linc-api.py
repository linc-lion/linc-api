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
from settings import api as settings, init_redis
from routes import url_patterns
import os
import asyncio
import signal

logger = logging.getLogger()
url_routes = url_patterns(settings['animals'])


# Tornado application
class Application(tornado.web.Application):
    def __init__(self):
        tornado.web.Application.__init__(self, url_routes, **settings)


async def shutdown(server, ioloop, signal=None):
    """Cleanup function to gracefully shut down the server"""
    if signal:
        logging.info(f'Received signal: {signal.name}')
    
    logging.info('Shutting down server...')
    server.stop()
    
    # Close Redis connection
    if settings['cache']:
        await settings['cache'].close()
    
    logging.info('Shutting down IO loop...')
    await asyncio.sleep(1)  # Give tasks a chance to complete
    ioloop.stop()


# Run server
async def main():
    try:
        # Initialize Redis connection
        settings['cache'] = await init_redis()
        
        app = Application()
        if len(logger.handlers) > 0:
            formatter = logging.Formatter("[%(levelname).1s %(asctime)s %(module)s:%(lineno)s] %(message)s", datefmt='%y%m%d %H:%M:%S')
            logger.handlers[0].setFormatter(formatter)
        if options.debug:
            logging.info('== Tornado in DEBUG mode ==============================')
            for key, cfg in settings.items():
                if key != 'cache':  # Skip cache object in debug output
                    logging.info(key + ' = ' + str(cfg))
            logging.info('=======================================================')
        
        port = int(os.environ.get("PORT", options.port))
        logging.info(f'Server starting on port: {port}')
        logging.info('API handlers:')
        for h in url_routes:
            logging.info(h)
        
        server = tornado.httpserver.HTTPServer(app)
        server.listen(port)
        
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(server, loop, signal=s))
            )
        
        # Keep the server running
        await asyncio.Event().wait()
        
    except Exception as e:
        logging.error(f"Failed to start server: {str(e)}")
        raise
    finally:
        logging.info("Server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())

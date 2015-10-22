#!/usr/bin/env python
# coding: utf-8

from handlers.base import VersionHandler
from handlers.error import ErrorHandler
from handlers.auth import AuthHandler
import sys
#from db.import2mongodb import ImportHandler
from handlers.animals import AnimalsHandler
from handlers.organizations import OrganizationsHandler
from handlers.users import UsersHandler
from handlers.imagesets import ImageSetsHandler,ImagesHandler
from handlers.cv import CVRequestsHandler,CVResultsHandler

# Defining routes
def url_patterns(animals='lions'):
    routes = [
        (r"/version/?", VersionHandler),
        # The handler above will be used only for import
        # data from pg in development phase
        #(r"/import", ImportHandler),
        (r"/"+animals+'/?', AnimalsHandler),

        #(r"/organizations/?", OrganizationsHandler),
        (r"/organizations/?$", OrganizationsHandler),
        (r"/organizations/(.*)$", OrganizationsHandler),
        (r"/organizations/(\w+)/(edit)$", OrganizationsHandler),

        (r"/users/?", UsersHandler),

        (r"/imagesets/?$", ImageSetsHandler),
        (r"/imagesets/(\w+$)", ImageSetsHandler),
        (r"/imagesets/(\w+)/(cvrequest)$", ImageSetsHandler),

        (r"/images/?", ImagesHandler),
        (r"/cvrequests/?", CVRequestsHandler),
        (r"/cvresults/?", CVResultsHandler)
    ]
    return routes

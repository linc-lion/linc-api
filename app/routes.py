#!/usr/bin/env python
# coding: utf-8

import sys
from handlers.base import VersionHandler
from handlers.error import ErrorHandler
from handlers.auth import AuthHandler
from handlers.animals import AnimalsHandler
from handlers.organizations import OrganizationsHandler
from handlers.users import UsersHandler
from handlers.imagesets import ImageSetsHandler
from handlers.images import ImagesHandler
from handlers.cvrequests import CVRequestsHandler
from handlers.cvresults import CVResultsHandler

# To import data
#from db.import2mongodb import ImportHandler

# Defining routes
def url_patterns(animals='lions'):
    routes = [
        (r"/version/?", VersionHandler),

        # The handler above will be used only for import
        # data from pg in development phase
        #(r"/import", ImportHandler),

        (r"/"+animals+"/?$", AnimalsHandler),
        (r"/"+animals+"/(\w+)/?$", AnimalsHandler),
        (r"/"+animals+"/(\w+)/(profile)$", AnimalsHandler),
        (r"/"+animals+"/(\w+)/(locations)$", AnimalsHandler),

        (r"/organizations/?$", OrganizationsHandler),
        (r"/organizations/(.*)$", OrganizationsHandler),

        (r"/users/?$", UsersHandler),
        (r"/users/(.*)$", UsersHandler),

        (r"/images/?$", ImagesHandler),
        (r"/images/(\w+$)", ImagesHandler),

        (r"/imagesets/?$", ImageSetsHandler),
        (r"/imagesets/(\w+)/?$", ImageSetsHandler),
        (r"/imagesets/(\w+)/(cvrequest)$", ImageSetsHandler),
        (r"/imagesets/(\w+)/(profile)$", ImageSetsHandler),

        (r"/cvrequests/?$", CVRequestsHandler),
        (r"/cvrequests/(\w+$)", CVRequestsHandler),

        (r"/cvresults/?$", CVResultsHandler),
        (r"/cvresults/(\w+$)", CVResultsHandler),
        (r"/cvresults/(\w+)/(list)$", CVResultsHandler)
    ]
    return routes

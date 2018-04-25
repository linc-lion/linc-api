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

from handlers.base import VersionHandler, DocHandler
from handlers.data_export import DataExportHandler
from handlers.auth import LoginHandler, LogoutHandler, CheckAuthHandler
from handlers.auth import RestorePassword, ChangePasswordHandler, RequestAccessHandler
from handlers.animals import AnimalsHandler
from handlers.animals_relatives import AnimalsRelativesHandler
from handlers.organizations import OrganizationsHandler
from handlers.users import UsersHandler
from handlers.imagesets import ImageSetsHandler
from handlers.images import ImagesHandler
from handlers.cvrequests import CVRequestsHandler
from handlers.cvresults import CVResultsHandler


# Defining routes
def url_patterns(animals='lions'):
    routes = [
        (r"/version/?", VersionHandler),
        (r"/auth/login/?", LoginHandler),
        (r"/auth/logout/?", LogoutHandler),
        (r"/auth/check", CheckAuthHandler),
        (r"/auth/recover", RestorePassword),
        (r"/auth/requestaccess", RequestAccessHandler),
        (r"/auth/changepassword", ChangePasswordHandler),
        (r"/data/export/?$", DataExportHandler),
        (r"/documentation.html", DocHandler),

        (r"/" + animals + "/?$", AnimalsHandler),
        (r"/" + animals + "/(\w+)/?$", AnimalsHandler),
        (r"/" + animals + "/(\w+)/(profile)/?$", AnimalsHandler),
        (r"/" + animals + "/(\w+)/(locations)/?$", AnimalsHandler),
        (r"/" + animals + "/(\w+)/(relatives)/?$", AnimalsRelativesHandler),
        (r"/" + animals + "/(\w+)/(relatives)/(\w+)/?$", AnimalsRelativesHandler),

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
        (r"/imagesets/(\w+)/(gallery)$", ImageSetsHandler),

        (r"/cvrequests/?$", CVRequestsHandler),
        (r"/cvrequests/(\w+$)", CVRequestsHandler),

        (r"/cvresults/?$", CVResultsHandler),
        (r"/cvresults/(\w+$)", CVResultsHandler),
        (r"/cvresults/(\w+)/(list)$", CVResultsHandler)
    ]
    return routes

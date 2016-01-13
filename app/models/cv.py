#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import sys; sys.path.append('../')
from datetime import datetime
from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType

class CVRequest(Model):
    requesting_organization_iid = IntType(required=True)
    iid = IntType(required=True)
    image_set_iid = IntType(required=True)
    status = StringType(required=True,default='registered')
    server_uuid = StringType(required=True)
    request_body = StringType(required=True,default='')
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'cvrequests'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Status:
        "registered" = the object was created but without connect to CV Server
        "queued", "processing", "finished", and "error"

    Indexes:
        db.cvrequests.createIndex( { "iid": 1 }, { unique: true } )
        db.cvrequests.createIndex( { "image_set_iid": 1 }, { unique: true } )
    """

class CVResult(Model):
    cvrequest_iid = IntType(required=True)
    iid = IntType(required=True)
    match_probability = StringType(required=True,default='[]')
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'cvresults'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Status:
        "queued", "processing", "finished", and "error"

    Indexes:
        db.cvresults.createIndex( { "cvrequest_iid": 1 }, { unique: true } )
        db.cvresults.createIndex( { "iid": 1 }, { unique: true } )
    """

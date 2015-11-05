#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from datetime import datetime
from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType

class CVRequest(Model):
    requesting_organization_iid = IntType(required=True)
    iid = IntType(required=True)
    image_set_iid = IntType(required=True)
    status = StringType(required=True,default='registered')
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())
    server_uuid = StringType(required=True)
    request_body = StringType(required=True,default='')

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
    status = StringType(required=True,default='queued')
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

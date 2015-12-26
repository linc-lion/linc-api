#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType,BooleanType
from datetime import datetime

class Organization(Model):
    name = StringType(required=True)
    iid = IntType(required=True)
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'organizations'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.organizations.createIndex( { "iid": 1 }, { unique: true } )
        db.organizations.createIndex( { "name": 1 }, { unique: true } )
    """

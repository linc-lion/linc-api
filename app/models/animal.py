#!/usr/bin/env python
# -*- coding: utf-8 -*-

from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType,BooleanType
from datetime import datetime

class Animal(Model):
    name = StringType(required=True)
    iid = IntType(required=True)
    organization_iid = IntType(required=True)
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())
    primary_image_set_iid = IntType(required=False,default=-1)
    trashed = BooleanType(required=True,default=False)

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'animals'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.['animals'].createIndex( { "name": 1 }, { unique: true } )
        db.['animals'].createIndex( { "iid": 1 }, { unique: true } )
    """

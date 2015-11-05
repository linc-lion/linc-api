#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType,FloatType,BooleanType
from schematics.types.compound import ListType
from datetime import datetime

class ImageSet(Model):
    animal_iid = IntType(required=False,default=None)
    iid = IntType(required=True)
    main_image_iid = IntType(required=False,default=None)
    uploading_organization_iid = IntType(required=True)
    uploading_user_iid = IntType(required=True,default=None)
    owner_organization_iid = IntType(required=True,default=None)
    is_verified = BooleanType(required=True,default=False)
    location = ListType(ListType(FloatType()))
    gender = StringType(required=False,default=None)
    is_primary = BooleanType(required=True,default=False)
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())
    date_of_birth = DateTimeType(required=False,default=None)
    tags = StringType(required=False,default='[]')
    date_stamp = StringType(required=False,default='-')
    notes = StringType(required=False)
    trashed = BooleanType(required=True,default=False)

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'imagesets'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.imagesets.createIndex( { "iid": 1 }, { unique: true } )
    """

class Image(Model):
    image_type = StringType(required=True)
    iid = IntType(required=True)
    image_set_iid = IntType(required=True,default=None)
    is_public = BooleanType(required=True,default=False)
    url = StringType(required=True)
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())
    trashed = BooleanType(required=True,default=False)

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'images'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.images.createIndex( { "iid": 1 }, { unique: true } )
    """

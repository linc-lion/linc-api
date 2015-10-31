#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from motorengine.fields import StringField,DateTimeField,\
        ReferenceField,BooleanField,IntField,URLField,FloatField,ListField
from motorengine.document import Document
from datetime import datetime

class ImageSet(Document):
    __collection__ = 'imagesets'
    animal_iid = IntField(required=False,default=None)
    iid = IntField(required=True,unique=True)
    main_image_iid = IntField(required=False,default=None)
    uploading_organization_iid = IntField(required=False,default=None)
    uploading_user_iid = IntField(required=False,default=None)
    owner_organization_iid = IntField(required=False,default=None)
    is_verified = BooleanField(required=True,default=False)
    location = ListField(ListField(FloatField()))
    gender = StringField(required=False,default=None)
    is_primary = BooleanField(required=True,default=False)
    created_at = DateTimeField(required=True,auto_now_on_insert=True)
    updated_at = DateTimeField(required=True,auto_now_on_insert=True)
    date_of_birth = DateTimeField(required=False,default=None)
    tags = StringField(required=False,default='[]')
    date_stamp = StringField(required=False,default='-')
    notes = StringField(required=False)
    trashed = BooleanField(required=True,default=False)

class Image(Document):
    __collection__ = 'images'
    image_type = StringField(required=True)
    iid = IntField(required=True,unique=True)
    image_set_iid = IntField(required=False,default=-1)
    is_public = BooleanField(required=True,default=False)
    url = StringField(required=True)
    created_at = DateTimeField(required=True,auto_now_on_insert=True)
    updated_at = DateTimeField(required=True,auto_now_on_insert=True)
    trashed = BooleanField(required=True,default=False)

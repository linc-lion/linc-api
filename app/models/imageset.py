#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from motorengine.fields import StringField,DateTimeField,\
        ReferenceField,BooleanField,IntField,URLField,FloatField,ListField
from motorengine.document import Document
from datetime import datetime

class ImageSet(Document):
    __collection__ = 'imagesets'
    animal_iid = IntField(required=False,default=-1)
    iid = IntField(required=True,unique=True)
    main_image_iid = IntField(required=False,default=-1)
    uploading_organization_iid = IntField(required=False,default=-1)
    uploading_user_iid = IntField(required=False,default=-1)
    owner_organization_iid = IntField(required=False,default=-1)
    is_verified = BooleanField(required=True,default=False)
    location = ListField(ListField(FloatField()))
    gender = StringField(required=False,default=None)
    is_primary = BooleanField(required=True,default=False)
    created_at = DateTimeField(required=True,default=datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.now())
    date_of_birth = DateTimeField(required=False,default=None)
    tags = StringField(required=False,default='[]')
    date_stamp = DateTimeField(required=False,default=None)
    notes = StringField(required=False)

class Image(Document):
    __collection__ = 'images'
    image_type = StringField(required=True)
    iid = IntField(required=True,unique=True)
    image_set_iid = IntField(required=False,default=-1)
    is_public = BooleanField(required=True,default=False)
    url = URLField(required=True)
    created_at = DateTimeField(required=True,default=datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.now())
    is_deleted = BooleanField(required=True,default=False)
    full_image_uid = StringField(required=True)
    thumbnail_image_uid = StringField(required=True)
    main_image_uid = StringField(required=True)

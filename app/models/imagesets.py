#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from monguo.field import StringField,DateTimeField,ReferenceField,BooleanField,LocationField,ListField,GenericDictField,EmailField,IntegerField,FloatField
from monguo.document import Document
import datetime

class ImageSet(Document):
    lion_id = StringField()
    main_image_id = StringField()
    uploading_organization_id = StringField()
    uploading_user_id = StringField()
    owner_organization_id = StringField()
    is_verified = BooleanField()
    latitude = FloatField()
    decimal = FloatField()
    longitude = FloatField()
    photo_date = DateTimeField(required=True,default=datetime.datetime.now())
    gender = StringField()
    is_primary = BooleanField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    date_of_birth = DateTimeField(required=True,default=datetime.datetime.now())
    tags = StringField()
    date_stamp = DateTimeField(required=True,default=datetime.datetime.now())
    notes = StringField()
    meta = {'collection':'imagesets'}

class Image(Document):
    image_type = StringField()
    image_set_id = ReferenceField(ImageSet,required=True)
    is_public = BooleanField()
    url = StringField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    is_deleted = BooleanField()
    full_image_uid = StringField()
    thumbnail_image_uid = StringField()
    main_image_uid = StringField()
    meta = {'collection':'images'}

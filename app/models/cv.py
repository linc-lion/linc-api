#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from motorengine.fields import StringField,DateTimeField,\
    BooleanField,ListField,IntField,FloatField
from motorengine.document import Document
from datetime import datetime

class CVRequest(Document):
    __collection__ = 'cvrequests'
    requesting_organization_iid = IntField(required=False,default=None)
    iid = IntField(required=True,unique=True)
    image_set_iid = IntField(required=False,unique=True,default=None)
    status = StringField(required=False,default='registered')
    created_at = DateTimeField(required=True,auto_now_on_insert=True)
    updated_at = DateTimeField(required=True,auto_now_on_insert=True)
    server_uuid = StringField(required=False,default=None)
    request_body = StringField(required=False,default='')

class CVResult(Document):
    __collection__ = 'cvresults'
    cvrequest_iid = IntField(required=False,default=None,unique=True)
    iid = IntField(required=True,unique=True)
    match_probability = StringField(required=True,default='[]')
    created_at = DateTimeField(required=True,auto_now_on_insert=True)
    updated_at = DateTimeField(required=True,auto_now_on_insert=True)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from motorengine.fields import StringField,DateTimeField,\
    BooleanField,ListField,IntField,FloatField
from motorengine.document import Document
from datetime import datetime

class CVRequest(Document):
    __collection__ = 'cvrequests'
    uploading_organization_iid = IntField(required=False,default=-1)
    iid = IntField(required=True,unique=True)
    image_set_iid = IntField(required=False,default=-1)
    status = StringField(required=False,default='registered')
    created_at = DateTimeField(required=True,default=datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.now())
    server_uuid = StringField(required=False,default=None)

class CVResult(Document):
    __collection__ = 'cvresults'
    cv_request_iid = IntField(required=False,default=-1)
    match_probability = StringField(required=True,default='[]')
    #[{'id':2,'value':0.44},{'id':3,'value':0.99}]
    #FloatField(required=False,default=0.0)
    created_at = DateTimeField(required=True,default=datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.now())
    #lion_iid = IntField(required=False,default=-1)

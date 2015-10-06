#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from monguo.field import StringField,DateTimeField,ReferenceField,BooleanField,LocationField,ListField,GenericDictField,EmailField,IntegerField,FloatField
from monguo.document import Document
import datetime

class CVRequests(Document):
    uploading_organization_id = StringField()
    image_set_id = StringField()
    status = StringField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    server_uuid = StringField()
    meta = {'collection':'cvrequests'}

class CVResults(Document):
    cv_request_id = StringField()
    match_probability = FloatField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    lion_id = StringField()
    meta = {'collection':'cvresults'}


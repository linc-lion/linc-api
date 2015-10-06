#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from monguo.field import StringField,DateTimeField,ReferenceField,BooleanField,LocationField,ListField,GenericDictField,EmailField,IntegerField,FloatField
from monguo.document import Document
from datetime import datetime

class User(Document):
    email = EmailField(required=True)
    organization_id = IntegerField(required=True)
    created_at = DateTimeField(required=True,default=datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.now())
    encrypted_password = StringField(required=True)
    remember_created_at = DateTimeField(required=True,default=datetime.now())
    sign_in_count = IntegerField()
    current_sign_in_at = DateTimeField(required=True,default=datetime.now())
    last_sign_in_at = DateTimeField(required=True,default=datetime.now())
    authentication_token = StringField()
    current_sign_in_ip = StringField()
    last_sign_in_ip = StringField()
    meta = {'collection':'users'}

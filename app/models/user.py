#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from motorengine.fields import StringField,DateTimeField,ReferenceField,\
    EmailField,IntField,BooleanField
from motorengine.document import Document
from datetime import datetime
from models.organization import Organization

class User(Document):
    __collection__ = 'users'
    email = EmailField(required=True,unique=True)
    iid = IntField(required=True,unique=True)
    organization_iid = IntField(required=False,default=-1)
    created_at = DateTimeField(required=True,auto_now_on_insert=True)
    updated_at = DateTimeField(required=True,auto_now_on_insert=True)
    encrypted_password = StringField(required=True)
    remember_created_at = DateTimeField(required=False)
    reset_password_token = StringField(required=False)
    reset_password_sent_at = DateTimeField(required=False,default=None)
    authentication_token = StringField(required=False,default=None)
    sign_in_count = IntField(required=False,default=0)
    current_sign_in_ip = StringField(required=False,default=None)
    current_sign_in_at = DateTimeField(required=False,default=None)
    last_sign_in_ip = StringField(required=False,default=None)
    last_sign_in_at = DateTimeField(required=False,default=None)
    admin = BooleanField(required=True,default=False)
    trashed = BooleanField(required=True,default=False)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from motorengine.field import StringField,DateTimeField,\
    BooleanField,LocationField,ListField,GenericDictField,EmailField,IntegerField
from motorengine.document import Document
import datetime

class ActiveAdminComment(Document):
    namespace = StringField()
    body = StringField()
    resource_id = StringField()
    resource_type = StringField()
    author_id = ReferenceField(AdminUser,required=True)
    author_type = StringField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    meta = {'collection':'active_admin_comment'}

class AdminUser(Document):
    email = EmailField(required=True,unique=True)
    encrypted_password = StringField(required=True)
    reset_password_token = StringField()
    reset_password_sent_at = DateTimeField(required=True,default=datetime.datetime.now())
    remember_created_at = DateTimeField(required=True,default=datetime.datetime.now())
    sign_in_count = IntegerField(required=True,default=0)
    current_sign_in_at = DateTimeField(required=True,default=datetime.datetime.now())
    last_sign_in_at = DateTimeField(required=True,default=datetime.datetime.now())
    current_sign_in_ip = StringField()
    last_sign_in_ip = StringField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    meta = {'collection':'admin_user'}

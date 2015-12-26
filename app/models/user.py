#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType,EmailType,BooleanType
from datetime import datetime

class User(Model):
    email = EmailType(required=True)
    iid = IntType(required=True)
    organization_iid = IntType(required=True,default=-1)
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())
    encrypted_password = StringType(required=True)
    sign_in_count = IntType(required=False,default=0)
    current_sign_in_ip = StringType(required=False,default=None)
    current_sign_in_at = DateTimeType(required=False,default=None)
    last_sign_in_ip = StringType(required=False,default=None)
    last_sign_in_at = DateTimeType(required=False,default=None)
    admin = BooleanType(required=True,default=False)

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'users'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.users.createIndex( { "iid": 1 }, { unique: true } )
        db.users.createIndex( { "email": 1 }, { unique: true } )
    """

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from motorengine.fields import StringField,DateTimeField,IntField,BooleanField
from motorengine.document import Document

class Organization(Document):
    __collection__ = "organizations"
    name = StringField(required=True,unique=True)
    iid = IntField(required=True,unique=True)
    created_at = DateTimeField(required=True,auto_now_on_insert=True)
    updated_at = DateTimeField(required=True,auto_now_on_insert=True)
    trashed = BooleanField(required=True,default=False)

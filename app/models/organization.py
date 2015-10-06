#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from monguo.field import StringField,DateTimeField,ReferenceField,BooleanField,LocationField,ListField,GenericDictField,EmailField,IntegerField,FloatField
from monguo.document import Document
import datetime

class Organization(Document):
    name = StringField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    meta = {'collection':organizations}

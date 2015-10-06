#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append('../')
from monguo.field import StringField,DateTimeField,ReferenceField,BooleanField,LocationField,ListField,GenericDictField,EmailField,IntegerField,FloatField
from monguo.document import Document
import datetime

animal = 'lion'
animals = 'lions'

class Animal(Document):
    name = StringField()
    organization_id = StringField()
    created_at = DateTimeField(required=True,default=datetime.datetime.now())
    updated_at = DateTimeField(required=True,default=datetime.datetime.now())
    primary_image_set_id = StringField()
    meta = {'collection':animals}

    @classmethod
    def set_collection(cls,collname):
        """ Changes the default collection name for a object in MongoDB """
        cls.meta = {'collection':collname}

    def list_animals(self):
        """ List animals in the database """
        pass # code for listing lions

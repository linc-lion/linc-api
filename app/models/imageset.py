#!/usr/bin/env python
# -*- coding: utf-8 -*-

# LINC is an open source shared database and facial recognition
# system that allows for collaboration in wildlife monitoring.
# Copyright (C) 2016  Wildlifeguardians
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information or to contact visit linclion.org or
# email tech@linclion.org

from schematics.models import Model
from schematics.types import ModelType, StringType, IntType, DateTimeType,\
    FloatType, BooleanType
from schematics.types.compound import ListType
from datetime import datetime


class TagLocation(Model):
    title = StringType(required=True, default='Home')
    value = IntType(required=True, default=10000)


class ImageSet(Model):
    animal_iid = IntType(required=False, default=None)
    iid = IntType(required=True)
    main_image_iid = IntType(required=False, default=None)
    uploading_organization_iid = IntType(required=True)
    uploading_user_iid = IntType(required=True, default=None)
    owner_organization_iid = IntType(required=True, default=None)
    is_verified = BooleanType(required=True, default=False)
    location = ListType(ListType(FloatType()))
    gender = StringType(required=False, default=None)
    date_of_birth = DateTimeType(required=False, default=None)
    tags = StringType(required=False, default='[]')
    date_stamp = StringType(required=False, default=None)
    notes = StringType(required=False)
    geopos_private = BooleanType(required=False, default=False)
    tag_location = ModelType(TagLocation, required=False, default=None)
    created_at = DateTimeType(required=True, default=datetime.now())
    updated_at = DateTimeType(required=True, default=datetime.now())

    @classmethod
    def collection(self, name=None):
        if not name:
            self.__collection__ = 'imagesets'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.imagesets.createIndex( { "iid": 1 }, { unique: true } )
        db.imagesets.createIndex( { "location": "2d" } )
    """


class Image(Model):
    image_type = StringType(required=True)  # old field
    image_tags = ListType(StringType, required=True, default=[])
    iid = IntType(required=True)
    image_set_iid = IntType(required=True, default=None)
    is_public = BooleanType(required=True, default=False)
    url = StringType(required=True)
    hashcheck = StringType(required=True, default='')
    filename = StringType(required=False, default='')
    exif_data = StringType(required=False, default='{}')
    joined = IntType(required=False, default=None)
    created_at = DateTimeType(required=True, default=datetime.now())
    updated_at = DateTimeType(required=True, default=datetime.now())

    @classmethod
    def collection(self, name=None):
        if not name:
            self.__collection__ = 'images'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.images.createIndex( { "iid": 1 }, { unique: true } )
    """

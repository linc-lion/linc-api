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
# For more information or to contact visit linclion.org or email tech@linclion.org

from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType,BooleanType
from datetime import datetime

class Animal(Model):
    name = StringType(required=True)
    iid = IntType(required=True)
    organization_iid = IntType(required=True)
    primary_image_set_iid = IntType(required=False,default=None)
    dead = BooleanType(required=False,default=False)
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'animals'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.['animals'].createIndex( { "name": 1 }, { unique: true } )
        db.['animals'].createIndex( { "iid": 1 }, { unique: true } )
    """

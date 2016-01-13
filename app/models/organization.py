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

import sys; sys.path.append('../')
from schematics.models import Model
from schematics.types import StringType,IntType,DateTimeType,BooleanType
from datetime import datetime

class Organization(Model):
    name = StringType(required=True)
    iid = IntType(required=True)
    created_at = DateTimeType(required=True,default=datetime.now())
    updated_at = DateTimeType(required=True,default=datetime.now())

    @classmethod
    def collection(self,name=None):
        if not name:
            self.__collection__ = 'organizations'
        else:
            self.__collection__ = name
        return self.__collection__

    """
    Indexes:
        db.organizations.createIndex( { "iid": 1 }, { unique: true } )
        db.organizations.createIndex( { "name": 1 }, { unique: true } )
    """

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

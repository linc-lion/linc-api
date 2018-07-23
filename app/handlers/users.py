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

from tornado.web import asynchronous
from tornado.gen import engine, coroutine, Task
from handlers.base import BaseHandler
from models.user import User
from bson import ObjectId as ObjId
from datetime import datetime
from schematics.exceptions import ValidationError
from lib.rolecheck import allowedRole, api_authenticated
from logging import info


class UsersHandler(BaseHandler):
    """A class that handles requests about users informartion
    """

    def query_id(self, user_id):
        """This method configures the query that will find an object"""
        try:
            query = {'iid': int(user_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(user_id)}
            except Exception as e:
                info(e)
                query = {'email': user_id}
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, user_id=None):
        if user_id:
            if user_id == 'list':
                objs = yield self.Users.find().to_list(None)
                orgs = yield self.db.organizations.find().to_list(None)
                orgnames = dict()
                for org in orgs:
                    orgnames[org['iid']] = org['name']
                for obj in objs:
                    del obj['encrypted_password']
                self.set_status(200)
                self.finish(self.json_encode(
                    {'status': 'success',
                     'data': self.list(objs, orgnames)}))
            elif user_id == 'conservationists':
                orgs = yield self.db.organizations.find().to_list(None)
                users = yield self.Users.find().to_list(None)
                orglist = dict()
                for org in orgs:
                    if org['name'] not in orglist.keys():
                        orglist[org['name']] = list()
                    for user in users:
                        if user['organization_iid'] == org['iid']:
                            orglist[org['name']].append(user['email'])
                rm = list()
                for k, v in orglist.items():
                    if len(v) == 0:
                        rm.append(k)
                for k in rm:
                    del orglist[k]
                self.response(200, 'Ok, it works.', orglist)
                return
            else:
                # return a specific user accepting as id the integer id, hash and name
                query = self.query_id(user_id)
                objs = yield self.Users.find_one(query)
                if objs:
                    objuser = objs
                    objuser['obj_id'] = str(objs['_id'])
                    self.switch_iid(objuser)
                    del objuser['_id']
                    objuser['organization_id'] = objuser['organization_iid']
                    del objuser['organization_iid']
                    del objuser['encrypted_password']

                    self.set_status(200)
                    self.finish(self.json_encode({'status': 'success', 'data': objuser}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status': 'error', 'message': 'not found'}))
        else:
            objs = yield self.Users.find().to_list(None)
            output = list()
            for x in objs:
                obj = dict(x)
                obj['obj_id'] = str(x['_id'])
                del obj['_id']
                del obj['encrypted_password']
                obj['organization_id'] = obj['organization_iid']
                del obj['organization_iid']
                self.switch_iid(obj)
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status': 'success', 'data': output}))

    @asynchronous
    @engine
    @api_authenticated
    @allowedRole('admin')
    def post(self):
        # create a new user
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(User)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid, User.collection())
        # encrypt password
        newobj['encrypted_password'] = self.encryptPassword(self.input_data['password'])
        orgiid = self.input_data['organization_id']
        orgexists = yield self.db.organizations.find_one({'iid': orgiid})
        if orgexists:
            newobj['organization_iid'] = orgiid
        else:
            self.response(409, "Organization referenced doesn't exist.")
            return
        try:
            newuser = User(newobj)
            newuser.validate()
            # the new object is valid, so try to save
            try:
                newsaved = yield self.Users.insert(newuser.to_native())
                output = newuser.to_native()
                output['obj_id'] = str(newsaved)
                output['organization_id'] = output['organization_iid']
                del output['organization_iid']
                self.switch_iid(output)
                del output['encrypted_password']
                self.finish(self.json_encode(
                    {'status': 'success',
                     'message': 'new user saved',
                     'data': output}))
            except Exception as e:
                # duplicated index error
                self.response(409, 'Key violation.')
        except ValidationError as e:
            # received data is invalid in some way
            self.response(400, 'Invalid input data. Errors: %s.' % (str(e)))

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def put(self, user_id=None):
        # update an user
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(User)
        fields_allowed_to_be_update = ['email', 'organization_iid', 'admin', 'password']
        if 'organization_id' in self.input_data.keys():
            orgiid = self.input_data['organization_id']
            orgexists = yield self.db.organizations.find_one({'iid': orgiid})
            if orgexists:
                update_data['organization_iid'] = orgiid
            else:
                self.response(409, "Organization referenced doesn't exist.")
                return
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in self.input_data.keys():
                update_ok = True
                break
        if user_id and update_ok:
            query = self.query_id(user_id)
            updobj = yield self.Users.find_one(query)
            if updobj:
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        updobj[field] = update_data[field]
                if 'password' in self.input_data.keys():
                    updobj['encrypted_password'] = self.encryptPassword(self.input_data['password'])
                updobj['updated_at'] = datetime.now()
                updid = ObjId(updobj['_id'])
                del updobj['_id']
                try:
                    updobj = User(updobj)
                    updobj.validate()
                    # the object is valid, so try to save
                    try:
                        updobj = updobj.to_native()
                        updobj['_id'] = updid
                        saved = yield self.Users.find_one_and_update({'_id': updid}, updobj)
                        info(saved)
                        output = updobj
                        output['obj_id'] = str(updid)
                        del output['_id']
                        # Change iid to id in the output
                        self.switch_iid(output)
                        del output['encrypted_password']
                        output['organization_id'] = output['organization_iid']
                        del output['organization_iid']
                        self.finish(self.json_encode({'status': 'success', 'message': 'user updated', 'data': output}))
                    except Exception as e:
                        # duplicated index error
                        self.response(409, 'Invalid data for update.')
                except ValidationError as e:
                    # received data is invalid in some way
                    self.response(400, 'Invalid input data. Errors: ' + str(e) + '.')
            else:
                self.response(404, 'User not found.')
        else:
            self.response(400, 'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def delete(self, user_id=None):
        # delete an user
        if user_id:
            query = self.query_id(user_id)
            updobj = yield self.Users.find_one(query)
            if updobj:
                iid = updobj['iid']
                # imageset - uploading_user_iid
                # Imagesets now will be uploaded by the admin iid
                imgsetrc = yield self.ImageSets.update_many(
                    {'uploading_user_iid': iid},
                    {'$set':
                        {'uploading_user_iid': self.current_user['id'],
                         'updated_at': datetime.now()}})
                info(imgsetrc)
                try:
                    updobj = yield self.Users.remove(query)
                    self.response(200, 'User successfully deleted.')
                except Exception as e:
                    info(e)
                    self.response(500, 'Fail to delete user.')
            else:
                self.response(404, 'User not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')

    def list(self, objs, orgnames=None):
        """ Implements the list output used for UI in the website
        """
        output = list()
        info(orgnames)
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            obj['email'] = x['email']
            if orgnames and x['organization_iid'] in orgnames.keys():
                obj['organization'] = orgnames[x['organization_iid']]
            else:
                obj['organization'] = '-'
            output.append(obj)
        return output

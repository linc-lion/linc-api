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
from tornado.gen import coroutine, engine, Task
from handlers.base import BaseHandler
from models.organization import Organization
from bson import ObjectId as ObjId
from datetime import datetime
from lib.rolecheck import allowedRole, api_authenticated
from logging import info


class OrganizationsHandler(BaseHandler):
    """A class that handles requests about organizations informartion"""
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')

    def query_id(self, org_id):
        """This method configures the query that will find an object"""
        try:
            query = {'iid': int(org_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(org_id)}
            except Exception as e:
                query = {'name': org_id}
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, org_id=None):
        if org_id:
            if org_id == 'list':
                objs = yield self.db.organizations.find().to_list(None)
                self.set_status(200)
                self.finish(
                    self.json_encode(
                        {'status': 'success',
                         'data': self.list(objs)}))
            else:
                # return a specific organization accepting as id the integer id, hash and name
                query = self.query_id(org_id)
                objs = yield self.db.organizations.find_one(query)
                if objs:
                    objorg = objs
                    objorg['id'] = objs['iid']
                    objorg['obj_id'] = str(objs['_id'])
                    del objorg['iid']
                    del objorg['_id']
                    self.set_status(200)
                    self.finish(self.json_encode({'status': 'success', 'data': objorg}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status': 'error', 'message': 'not found'}))
        else:
            # return a list of organizations
            objs = yield self.db.organizations.find().to_list(None)
            output = list()
            for x in objs:
                obj = dict(x)
                obj['obj_id'] = str(x['_id'])
                del obj['_id']
                self.switch_iid(obj)
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status': 'success', 'data': output}))

    @asynchronous
    @engine
    @api_authenticated
    @allowedRole('admin')
    def post(self):
        # create a new organization
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(Organization)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid, Organization.collection())
        try:
            neworg = Organization(newobj)
            neworg.validate()
            # the new object is valid, so try to save
            try:
                newsaved = yield self.db.organizations.insert(neworg.to_native())
                output = neworg.to_native()
                info(output)
                output['obj_id'] = str(newsaved)
                # Change iid to id in the output
                self.switch_iid(output)
                self.finish(self.json_encode({'status': 'success', 'message': 'new organization saved', 'data': output}))
            except Exception as e:
                # duplicated index error
                self.response(409, 'Duplicated name for an organization.')
        except Exception as e:
            # received data is invalid in some way
            self.response(400, 'Invalid input data.')

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def put(self, org_id=None):
        # update an organization
        # parse data recept by PUT and get only fields of the object
        update_data = self.input_data
        fields_allowed_to_be_update = ['name']
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if org_id and update_ok:
            query = self.query_id(org_id)
            updobj = yield self.db.organizations.find_one(query)
            if updobj:
                updict = dict()
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        updict[field] = update_data[field]
                try:
                    if updict:
                        updict['updated_at'] = datetime.now()
                        updid = updobj['_id']
                        # the object is valid, so try to save
                        try:
                            saved = yield self.db.organizations.update(
                                {'_id': updid},
                                {'$set': updict})
                            info(saved)
                            output = updobj
                            output['obj_id'] = str(updid)
                            del output['_id']
                            for k, v in updict.items():
                                output[k] = v
                            # Change iid to id in the output
                            self.switch_iid(output)
                            self.finish(self.json_encode({'status': 'success', 'message': 'organization updated', 'data': output}))
                        except Exception as e:
                            # duplicated index error
                            self.response(409, 'Duplicated name for an organization.')
                    else:
                        self.response(400, 'No data provided to be updated.')
                except Exception as e:
                    # received data is invalid in some way
                    self.response(400, 'Invalid input data.')
            else:
                self.response(404, 'Organization not found.')
        else:
            self.response(400, 'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def delete(self, org_id=None):
        # delete an organization
        if org_id:
            query = self.query_id(org_id)
            updobj = yield self.db.organizations.find_one(query)
            if updobj:
                # check for references
                iid = updobj['iid']
                # user - organization_iid
                userrc = yield self.Users.update_many(
                    {'organization_iid': iid},
                    {'$set': {'organization_iid': self.current_user['org_id'],
                              'updated_at': datetime.now()}})
                info(userrc)
                # imageset - uploading_organization_iid
                # imageset - owner_organization_iid
                imgsetrc1 = yield self.ImageSets.update_many(
                    {'uploading_organization_iid': iid},
                    {'$set':
                        {'uploading_organization_iid': self.current_user['org_id'],
                         'updated_at': datetime.now()}})
                info(imgsetrc1)
                imgsetrc2 = yield self.ImageSets.update_many({'owner_organization_iid': iid}, {'$set': {'owner_organization_iid': self.current_user['org_id'], 'updated_at': datetime.now()}})
                info(imgsetrc2)
                # animal - organization_iid
                animalsrc = yield self.Animals.update_many({'organization_iid': iid}, {'$set': {'organization_iid': self.current_user['org_id'], 'updated_at': datetime.now()}})
                info(animalsrc)
                # cvrequest - uploading_organization_iid
                cvreqrc = yield self.CVRequests.update_many({'requesting_organization_iid': iid}, {'$set': {'requesting_organization_iid': self.current_user['org_id'], 'updated_at': datetime.now()}})
                info(cvreqrc)
                try:
                    updobj = yield self.db.organizations.remove(query)
                    self.response(200, 'Organization successfully deleted.')
                except Exception as e:
                    self.response(500, 'Fail to delete organization.')
            else:
                self.response(404, 'Organization not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have an organization id.')

    def list(self, objs):
        """ Implements the list output used for UI in the website
        """
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            obj['name'] = x['name']
            output.append(obj)
        return output

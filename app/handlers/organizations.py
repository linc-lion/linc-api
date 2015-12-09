#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine,engine,Task
from handlers.base import BaseHandler
from models.organization import Organization
from bson import ObjectId as ObjId
from json import loads
from tornado.escape import json_decode
from datetime import datetime
from lib.rolecheck import allowedRole, refusedRole, api_authenticated
from logging import info

class OrganizationsHandler(BaseHandler):
    """A class that handles requests about organizations informartion"""

    def query_id(self,org_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(org_id) }
        except:
            try:
                query = { '_id' : ObjId(org_id) }
            except:
                query = { 'name' : org_id}
        query['trashed'] = trashed
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, org_id=None):
        trashed = self.get_argument('trashed',False)
        if trashed:
            if trashed == '*':
                trashed = { '$in' : [True,False] }
            else:
                trashed = (trashed.lower() == 'true')
        if org_id:
            if org_id == 'list':
                # return a list of organizations for the website
                # ORM way
                #objs = yield Organization.objects.find_all()
                # Motor way
                objs = yield self.settings['db'].organizations.find({'trashed':trashed}).to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs)}))
            else:
                # return a specific organization accepting as id the integer id, hash and name
                query = self.query_id(org_id,trashed)
                objs = yield self.settings['db'].organizations.find_one(query)
                if objs:
                    objorg = objs
                    objorg['id'] = objs['iid']
                    objorg['obj_id'] = str(objs['_id'])
                    del objorg['iid']
                    del objorg['_id']
                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':objorg}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            # return a list of organizations
            objs = yield self.settings['db'].organizations.find({'trashed':trashed}).to_list(None)
            output = list()
            for x in objs:
                obj = dict(x)
                obj['obj_id'] = str(x['_id'])
                del obj['_id']
                self.switch_iid(obj)
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status':'success','data':output}))

    @asynchronous
    @engine
    @api_authenticated
    @allowedRole('admin')
    def post(self):
        # create a new organization
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(Organization)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,Organization.collection())
        try:
            neworg = Organization(newobj)
            neworg.validate()
            # the new object is valid, so try to save
            try:
                newsaved = yield self.settings['db'].organizations.insert(neworg.to_native())
                output = neworg.to_native()
                print(output)
                output['obj_id'] = str(newsaved)
                # Change iid to id in the output
                self.switch_iid(output)
                self.finish(self.json_encode({'status':'success','message':'new organization saved','data':output}))
            except:
                # duplicated index error
                self.dropError(409,'duplicated name for an organization')
        except:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data.')

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def put(self, org_id=None):
        # update an organization
        # parse data recept by PUT and get only fields of the object
        update_data = self.input_data
        fields_allowed_to_be_update = ['name','trashed']
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if org_id and update_ok:
            query = self.query_id(org_id)
            if 'trashed' in update_data.keys():
                del query['trashed']
            updobj = yield self.settings['db'].organizations.find_one(query)
            if updobj:
                updict = dict()
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        #if isinstance(update_data[field],str):
                        #    updict[field] =  "'" + str(update_data[field]) + "'"
                        #else:
                        #    updict[field] = str(update_data[field])
                        updict[field] = update_data[field]
                if True:
                #try:
                    if updict:
                        updict['updated_at'] = datetime.now()
                        updid = updobj['_id']
                        # the object is valid, so try to save
                        #try:
                        if True:
                            saved = yield self.settings['db'].organizations.update({'_id':updid},{'$set' : updict})
                            output = updobj
                            output['obj_id'] = str(updid)
                            del output['_id']
                            for k,v in updict.items():
                                output[k] = v
                            # Change iid to id in the output
                            self.switch_iid(output)
                            self.finish(self.json_encode({'status':'success','message':'organization updated','data':output}))
                        #except:
                        else:
                            # duplicated index error
                            self.dropError(409,'duplicated name for an organization')
                    else:
                        self.dropError(400,'No data provided to be updated')
                #except:
                else:
                    # received data is invalid in some way
                    self.dropError(400,'Invalid input data.')
            else:
                self.dropError(404,'organization not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def delete(self, org_id=None):
        # delete an organization
        if org_id:
            query = self.query_id(org_id)
            updobj = yield self.settings['db'].organizations.find_one(query)
            if updobj:
                # check for references
                refcount = 0
                iid = updobj['iid']
                # user - organization_iid
                userrc = yield self.settings['db'].users.find({'organization_iid':iid,'trashed':False}).count()
                info('Checking references in users - organization_iid:' + str(userrc))
                refcount += userrc
                # imageset - uploading_organization_iid
                # imageset - owner_organization_iid
                imgsetrc = yield self.settings['db'].imagesets.find({'$or' : [{'uploading_organization_iid':iid},{'owner_organization_iid':iid},{'trashed':False}]}).count()
                info('Checking references in imagesets:' + str(imgsetrc))
                refcount += imgsetrc
                # animal - organization_iid
                animalsrc = yield self.settings['db'][self.settings['animals']].find({'organization_iid':iid,'trashed':False}).count()
                info('Checking references in animals(lions):' + str(animalsrc))
                refcount += animalsrc
                # cvrequest - uploading_organization_iid
                cvreqrc = yield self.settings['db'].cvrequests.find({'uploading_organization_iid':iid,'trashed':False}).count()
                info('Checking references in cvrequests:' + str(cvreqrc))
                refcount += cvreqrc
                if refcount > 0:
                    self.dropError(417,"organization can't be deleted because it has references in the database.")
                else:
                    try:
                        updobj = yield self.settings['db'].organizations.update(query,{'$set':{'trashed':True,'updated_at':datetime.now()}})
                        self.setSuccess(200,'organization successfully deleted')
                    except:
                        self.dropError(500,'fail to delete organization')
            else:
                self.dropError(404,'organization not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    def list(self,objs):
        """ Implements the list output used for UI in the website
        """
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            obj['name'] = x['name']
            output.append(obj)
        return output

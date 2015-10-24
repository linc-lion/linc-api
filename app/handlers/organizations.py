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

class OrganizationsHandler(BaseHandler):
    """A class that handles requests about organizations informartion
    """
    @asynchronous
    @coroutine
    def get(self, org_id=None):
        if org_id:
            if org_id == 'list':
                # return a list of organizations for the website
                # ORM way
                #objs = yield Organization.objects.find_all()
                # Motor way
                objs = yield self.settings['db'].organizations.find().to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs)}))
            else:
                # return a specific organization accepting as id the integer id, hash and name
                try:
                    query = { 'iid' : int(org_id) }
                except:
                    try:
                        query = { 'id' : ObjId(org_id) }
                    except:
                        query = { 'name' : org_id}
                objs = yield Organization.objects.filter(**query).limit(1).find_all()
                if len(objs) > 0:
                    objorg = objs[0].to_son()
                    objorg['id'] = objs[0].iid
                    objorg['obj_id'] = str(objs[0]._id)
                    del objorg['iid']
                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':objorg}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            # return a list of organizations
            objs = yield Organization.objects.find_all()
            output = list()
            for x in objs:
                obj = x.to_son()
                obj['obj_id'] = str(x._id)
                obj['id'] = obj['iid']
                del obj['iid']
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status':'success','data':output}))

    def put(self, org_id):
        # update an organization
        pass

    @asynchronous
    @engine
    def post(self):
        # create a new organization
        # parse data recept by POST and get only fields of the
        newobj = self.parseInput(Organization)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,Organization.__collection__)
        try:
            neworg = Organization(**newobj)
            if neworg.validate():
                # the new object is valid, so try to save
                try:
                    newsaved = yield neworg.save()
                    output = newsaved.to_son()
                    output['obj_id'] = str(newsaved._id)
                    # Change iid to id in the output
                    self.switch_iid(output)
                    self.finish(self.json_encode({'status':'success','message':'new organization saved','data':output}))
                except:
                    # duplicated index error
                    self.dropError(409,'duplicated name for an organization')
        except:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data.')

    def delete(self, item_id):
        # delete an organization
        pass

    def list(self,objs):
        """ Implements the list output used for UI in the website """
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            obj['name'] = x['name']
            output.append(obj)
        return output

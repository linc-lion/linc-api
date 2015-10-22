#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine
from handlers.base import BaseHandler
from models.organization import Organization
from bson import ObjectId as ObjId

class OrganizationsHandler(BaseHandler):
    """A class that handles requests about organizations informartion
    """
    @asynchronous
    @coroutine
    def get(self, org_id=None, edit=False):
        if org_id:
            if org_id == 'list':
                # return a list of organizations for the website
                objs = yield Organization.objects.find_all()
                output = list()
                for x in objs:
                    obj = dict()
                    obj['id'] = x.iid
                    obj['name'] = x.name
                    output.append(obj)
                self.finish(self.json_encode({'status':'success','data':output}))
            elif edit:
                pass
            else:
                # return a specific organization accepting as id the integer id, hash and name
                try:
                    query = { 'iid' : int(org_id) }
                except:
                    if len(org_id) > 23:
                        query = { 'id' : ObjId(org_id) }
                    else:
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
            self.finish(self.json_encode({'status':'success','data':output}))

    def put(self, org_id):
        # update an organization
        pass

    def post(self):
        # create a new organization
        pass

    def delete(self, item_id):
        # delete an organization
        pass

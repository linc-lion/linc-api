#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.cv import CVRequest
from bson import ObjectId as ObjId
from datetime import datetime
from schematics.exceptions import ValidationError
from lib.rolecheck import allowedRole, refusedRole, api_authenticated

class CVRequestsHandler(BaseHandler):
    """A class that handles requests about CV indentification informartion
    """

    def query_id(self,req_id):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(req_id) }
        except:
            try:
                query = { '_id' : ObjId(req_id) }
            except:
                self.dropError(400,'invalid id key')
                return
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, req_id=None):
        if req_id:
            if req_id == 'list':
                objs = yield self.settings['db'].cvrequests.find().to_list(None)
                self.set_status(200)
                output = yield Task(self.list,objs)
                self.finish(self.json_encode({'status':'success','data':output}))
            else:
                query = self.query_id(req_id)
                obj = yield self.settings['db'].cvrequests.find_one(query)
                if obj:
                    objreq = obj
                    objreq['id'] = obj['iid']
                    objreq['obj_id'] = str(obj['_id'])
                    del objreq['iid']
                    del objreq['_id']
                    objreq['image_set_id'] = objreq['image_set_iid']
                    del objreq['image_set_iid']
                    objreq['requesting_organization_id'] = objreq['requesting_organization_iid']
                    del objreq['requesting_organization_iid']
                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':objreq}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            objs = yield self.settings['db'].cvrequests.find().to_list(None)
            output = list()
            for x in objs:
                obj = dict(x)
                obj['obj_id'] = str(x['_id'])
                del obj['_id']
                self.switch_iid(obj)
                obj['image_set_id'] = obj['image_set_iid']
                del obj['image_set_iid']
                obj['requesting_organization_id'] = obj['requesting_organization_iid']
                del obj['requesting_organization_iid']
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status':'success','data':output}))

    @asynchronous
    @engine
    @api_authenticated
    def post(self,*kwargs):
        # create a new req
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(CVRequest)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,CVRequest.collection())
        # prepare new obj
        dt = datetime.now()
        newobj['created_at'] = dt
        newobj['updated_at'] = dt
        fields_needed = ['requesting_organization_id','image_set_id','status',
        'server_uuid','request_body']
        for field in fields_needed:
            if field not in self.input_data.keys():
                self.dropError(400,'you need to provide the field '+field)
                return
            else:
                newobj[field] = self.input_data[field]
        imgsetid = self.input_data['image_set_id']
        isexists = yield self.settings['db'].imagesets.find_one({'iid':imgsetid,'trashed':False})
        if isexists:
            newobj['image_set_iid'] = imgsetid
            del newobj['image_set_id']
        else:
            self.dropError(409,"image set id referenced doesn't exist")
            return
        orgid = self.input_data['requesting_organization_id']
        orge = yield self.settings['db'].organizations.find_one({'iid':orgid,'trashed':False})
        if orge:
            newobj['requesting_organization_iid'] = orgid
            del newobj['requesting_organization_id']
        else:
            self.dropError(409,"organization id referenced doesn't exist")
            return

        try:
            newreq = CVRequest(newobj)
            newreq.validate()
            try:
                newsaved = yield self.settings['db'][CVRequest.collection()].insert(newreq.to_native())
                output = newreq.to_native()
                output['obj_id'] = str(newsaved)
                output['image_set_id'] = newreq['image_set_iid']
                del output['image_set_iid']
                output['requesting_organization_id'] = newreq['requesting_organization_iid']
                del output['requesting_organization_iid']
                self.switch_iid(output)
                self.finish(self.json_encode({'status':'success','message':'new cv request saved','data':output}))
            except:
                # duplicated index error
                self.dropError(409,'key violation')
        except ValidationError, e:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data. Impossible to validate the new cv request.'+e.messages)
            return

    @asynchronous
    @coroutine
    @api_authenticated
    def put(self, req_id=None):
        # update an req
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(CVRequest)
        fields_allowed_to_be_update = ['requesting_organization_id','image_set_id','status',
        'server_uuid','request_body']
        if 'image_set_id' in self.input_data.keys():
            imgiid = self.input_data['image_set_id']
            imgset = yield self.settings['db'].imagesets.find_one({'iid':imgiid,'trashed':False})
            if imgset:
                update_data['image_set_iid'] = imgiid
            else:
                self.dropError(409,"image set referenced doesn't exist")
                return
        if 'requesting_organization_id' in self.input_data.keys():
            orgiid = self.input_data['requesting_organization_id']
            orgset = yield self.settings['db'].organizations.find_one({'iid':orgiid,'trashed':False})
            if orgset:
                update_data['requesting_organization_iid'] = orgiid
            else:
                self.dropError(409,"organization referenced doesn't exist")
                return
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if req_id and update_ok:
            query = self.query_id(req_id)
            updobj = yield self.settings['db'].cvrequests.find_one(query)
            if updobj:
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        #cmd = "updobj."+field+" = "
                        if isinstance(update_data[field],str):
                            updobj[field] = "'" + str(update_data[field]) + "'"
                        else:
                            updobj[field] = str(update_data[field])
                updobj['updated_at'] = datetime.now()
                try:
                    objid = ObjId(str(updobj['_id']))
                    del updobj['_id']
                    updreq = CVRequest(updobj)
                    updreq.validate()
                    try:
                        updated = yield self.settings['db'][CVRequest.collection()].update({'_id':objid},updreq.to_native())
                        output = updreq.to_native()
                        output['obj_id'] = str(objid)
                        # Change iid to id in the output
                        self.switch_iid(output)
                        output['image_set_id'] = output['image_set_iid']
                        del output['image_set_iid']
                        output['requesting_organization_id'] = output['requesting_organization_iid']
                        del output['requesting_organization_iid']
                        self.finish(self.json_encode({'status':'success','message':'image updated','data':output}))
                    except:
                        # duplicated index error
                        self.dropError(409,'key violation')
                except:
                    # received data is invalid in some way
                    self.dropError(400,'Invalid input data.')
            else:
                self.dropError(404,'cv request not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, req_id=None):
        # delete a req
        if req_id:
            query = self.query_id(req_id)
            updobj = yield self.settings['db'].cvrequests.find_one(query)
            if updobj:
                # removing cvrequest and cvresult related and they will be added in
                # a history collection
                try:
                    # get cvresult if it exists
                    cvres = yield self.settings['db'].cvresults.find_one({'cv_request_iid':req_id})
                    if cvres:
                        print(cvres)
                        idcvres = ObjId(str(cvres['_id']))
                        del cvres['_id']
                        print(cvres)
                        newhres = yield self.settings['db'].cvresults_history.insert(cvres)
                        cvres = yield self.settings['db'].cvresults.remove({'_id':idcvres})
                    del updobj['_id']
                    newhreq = yield self.settings['db'].cvrequests_history.insert(updobj)
                    cvreq = yield self.settings['db'].cvrequests.remove(query)
                    self.setSuccess(200,'cvrequest successfully deleted')
                except:
                    self.dropError(500,'fail to delete cvrequest')
            else:
                self.dropError(404,'cvrequest not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    @asynchronous
    @engine
    def list(self,objs,callback=None):
        """ Implements the list output used for UI in the website
        """
        output = list()
        cvresl = yield self.settings['db'].cvresults.find().to_list(None)
        cvresd = dict()
        for cvres in cvresl:
            cvresd[cvres['cvrequest_iid']] = {'cvres_id':cvres['iid'],'cvres_obj_id':str(cvres['_id']) }
        for x in objs:
            obj = dict()
            obj['cvreq_id'] = x['iid']
            obj['cvreq_obj_id'] = x['_id']
            obj['status'] = x['status']
            obj['imageset_id'] = x['image_set_iid']
            obj['organization_id'] = x['requesting_organization_iid']
            if x['iid'] in cvresd.keys():
                obj['cvres_id'] = cvresd[x['iid']]['cvres_id']
                obj['cvres_obj_id'] = cvresd[x['iid']]['cvres_obj_id']
            else:
                obj['cvres_id'] = None
                obj['cvres_obj_id'] = None
            output.append(obj)
        callback(output)

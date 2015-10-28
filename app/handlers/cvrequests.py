#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.cv import CVRequest
from bson import ObjectId as ObjId
from datetime import datetime

class CVRequestsHandler(BaseHandler):
    """A class that handles requests about CV indentification informartion
    """

    def query_id(self,req_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(req_id) }
        except:
            try:
                query = { 'id' : ObjId(req_id) }
            except:
                self.dropError(400,'invalid id key')
                return
        query['trashed'] = trashed
        print(query)
        return query

    @asynchronous
    @coroutine
    def get(self, req_id=None):
        trashed = self.get_argument('trashed',False)
        if trashed:
            if trashed.lower() == 'true':
                trashed = True
            else:
                trashed = False
        print(req_id)
        if req_id:
            if req_id == 'list':
                objs = yield self.settings['db'].cvrequests.find({'trashed':trashed}).to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs)}))
            else:
                query = self.query_id(req_id,trashed)
                print(query)
                objs = yield req.objects.filter(**query).limit(1).find_all()
                if len(objs) > 0:
                    objreq = objs[0].to_son()
                    objreq['id'] = objs[0].iid
                    objreq['obj_id'] = str(objs[0]._id)
                    del objreq['iid']

                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':objreq}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            objs = yield self.settings['db'].cvrequests.find({'trashed':trashed}).to_list(None)
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
    def post(self):
        # create a new req
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(CVRequest)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,CVRequest.__collection__)
        # prepare new obj
        dt = datetime.now()
        newobj['created_at'] = dt
        newobj['updated_at'] = dt
        fields_needed = ['requesting_organization_id','iid','image_set_id','status',
        'server_uuid','request_body']
        for field in fields_needed:
            if field not in self.input_data.keys():
                self.dropError(400,'you need to provide the field '+field)
                return
            else:
                newobj[field] = self.input_data[field]
        print(newobj)
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
            newreq = CVRequest(**newobj)
            if newreq.validate():
                # the new object is valid, so try to save
                try:
                    newsaved = yield newreq.save()
                    output = newsaved.to_son()
                    output['obj_id'] = str(newsaved._id)
                    self.switch_iid(output)
                    self.finish(self.json_encode({'status':'success','message':'new cv request saved','data':output}))
                except:
                    # duplicated index error
                    self.dropError(409,'key violation')
        except:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data.')

    @asynchronous
    @coroutine
    def put(self, req_id=None):
        # update an req
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(CVRequest)
        fields_allowed_to_be_update = ['requesting_organization_id','iid','image_set_id','status',
        'server_uuid','request_body','trashed']
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
            if 'trashed' in update_data.keys():
                del query['trashed']
            updobj = yield CVRequest.objects.filter(**query).limit(1).find_all()
            if len(updobj) > 0:
                updobj = updobj[0]
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        cmd = "updobj."+field+" = "
                        if isinstance(update_data[field],str):
                            cmd = cmd + "'" + str(update_data[field]) + "'"
                        else:
                            cmd = cmd + str(update_data[field])
                        exec(cmd)
                updobj.updated_at = datetime.now()
                try:
                    if updobj.validate():
                        # the object is valid, so try to save
                        try:
                            saved = yield updobj.save()
                            output = saved.to_son()
                            output['obj_id'] = str(saved._id)
                            # Change iid to id in the output
                            self.switch_iid(output)
                            output['image_set_id'] = output['image_set_iid']
                            del output['image_set_iid']
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
    def delete(self, req_id=None):
        # delete an req
        if req_id:
            query = self.query_id(req_id)
            updobj = yield self.settings['db'].cvrequests.find_one(query)
            if updobj:
                # removing cvrequest and cvresult related and they will be added in
                # a history collection
                #try:
                if True:
                    # get cvresult if it exists
                    cvres = yield self.settings['db'].cvresults.find_one({'cv_request_iid':req_id})
                    if cvres:
                        idcvres = ObjId(str(cvres['_id']))
                        del cvres['_id']
                        newhres = yield self.settings['db'].cvresults_history.insert(cvres)
                        cvres = yield self.settings['db'].cvresults.remove({'_id':idcvres})
                    idcvreq = ObjId(str(updobj))
                    del updobj['_id']
                    newhreq = yield self.settings['db'].cvrequests_history.insert(updobj)
                    cvreq = yield self.settings['db'].cvrequests.remove({'_id':idcvreq})
                    self.setSuccess(200,'cvrequest successfully deleted')
                #except:
                else:
                    self.dropError(500,'fail to delete cvrequest')
            else:
                self.dropError(404,'cvrequest not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    def list(self,objs):
        """ Implements the list output used for UI in the website
        """
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            output.append(obj)
        return output

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.cv import CVResult
from bson import ObjectId as ObjId
from datetime import datetime

class CVResultsHandler(BaseHandler):
    """A class that handles requests about CV identificaiton results informartion
    """

    def query_id(self,res_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(res_id) }
        except:
            try:
                query = { 'id' : ObjId(res_id) }
            except:
                self.dropError(400,'invalid id key')
                return
        query['trashed'] = trashed
        print(query)
        return query

    @asynchronous
    @coroutine
    def get(self, res_id=None):
        trashed = self.get_argument('trashed',False)
        if trashed:
            if trashed.lower() == 'true':
                trashed = True
            else:
                trashed = False
        print(res_id)
        if res_id:
            if res_id == 'list':
                objs = yield self.settings['db'].cvresults.find({'trashed':trashed}).to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs)}))
            else:
                query = self.query_id(res_id,trashed)
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
            objs = yield self.settings['db'].cvresults.find({'trashed':trashed}).to_list(None)
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
        newobj = self.parseInput(CVResult)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,CVResult.__collection__)
        # prepare new obj
        dt = datetime.now()
        newobj['created_at'] = dt
        newobj['updated_at'] = dt
        fields_needed = ['match_probability','cvrequest_iid']
        for field in fields_needed:
            if field not in self.input_data.keys():
                self.dropError(400,'you need to provide the field '+field)
                return
            else:
                newobj[field] = self.input_data[field]
        print(newobj)
        cvid = self.input_data['cvrequest_id']
        cvexists = yield self.settings['db'].cvrequests.find_one({'iid':cvid,'trashed':False})
        if cvexists:
            newobj['cvrequest_iid'] = imgsetid
            del newobj['cvrequest_id']
        else:
            self.dropError(409,"cv request id referenced doesn't exist")
            return
        try:
            newres = CVResult(**newobj)
            if newres.validate():
                # the new object is valid, so try to save
                try:
                    newsaved = yield newres.save()
                    output = newsaved.to_son()
                    output['obj_id'] = str(newsaved._id)
                    self.switch_iid(output)
                    self.finish(self.json_encode({'status':'success','message':'new cv results saved','data':output}))
                except:
                    # duplicated index error
                    self.dropError(409,'key violation')
        except:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data.')

    @asynchronous
    @coroutine
    def put(self, res_id=None):
        # update an req
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(CVResult)
        fields_allowed_to_be_update = ['match_probability']
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if res_id and update_ok:
            query = self.query_id(res_id)
            if 'trashed' in update_data.keys():
                del query['trashed']
            updobj = yield CVResult.objects.filter(**query).limit(1).find_all()
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
                self.dropError(404,'cv result not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    def delete(self, res_id=None):
        # delete an req
        if res_id:
            query = self.query_id(res_id)
            updobj = yield self.settings['db'].cvresults.find_one(query)
            if updobj:
                # removing cvrequest and cvresult related and they will be added in
                # a history collection
                #try:
                if True:
                    idcvres = ObjId(str(updobj))
                    del updobj['_id']
                    newhres = yield self.settings['db'].cvresults_history.insert(updobj)
                    cvres = yield self.settings['db'].cvresults.remove({'_id':idcvreq})
                    self.setSuccess(200,'cvrequest successfully deleted')
                #except:
                else:
                    self.dropError(500,'fail to delete cvresult')
            else:
                self.dropError(404,'cvresult not found')
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

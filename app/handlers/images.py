#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.imageset import Image
from bson import ObjectId as ObjId
from datetime import datetime

class ImagesHandler(BaseHandler):
    """A class that handles requests about images informartion
    """

    def query_id(self,image_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(image_id) }
        except:
            try:
                query = { 'id' : ObjId(image_id) }
            except:
                self.dropError(400,'invalid id key')
                return
        query['trashed'] = trashed
        print(query)
        return query

    @asynchronous
    @coroutine
    def get(self, image_id=None):
        trashed = self.get_argument('trashed',False)
        if trashed:
            if trashed.lower() == 'true':
                trashed = True
            else:
                trashed = False
        print(image_id)
        if image_id:
            if image_id == 'list':
                objs = yield self.settings['db'].images.find({'trashed':trashed}).to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs)}))
            else:
                # return a specific image accepting as id the integer id, hash and name
                query = self.query_id(image_id,trashed)
                print(query)
                objs = yield Image.objects.filter(**query).limit(1).find_all()
                if len(objs) > 0:
                    objimage = objs[0].to_son()
                    objimage['id'] = objs[0].iid
                    objimage['obj_id'] = str(objs[0]._id)
                    del objimage['iid']

                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':objimage}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            # return a list of images
            #objs = yield Image.objects.find_all()
            objs = yield self.settings['db'].images.find({'trashed':trashed}).to_list(None)
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
        # create a new image
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(Image)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,Image.__collection__)
        # prepare new obj
        dt = datetime.now()
        newobj['created_at'] = dt
        newobj['updated_at'] = dt
        fields_needed = ['is_deleted','image_set_id',
        'is_public','url','image_type']
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

        try:
            newimage = Image(**newobj)
            if newimage.validate():
                # the new object is valid, so try to save
                try:
                    newsaved = yield newimage.save()
                    output = newsaved.to_son()
                    output['obj_id'] = str(newsaved._id)
                    self.switch_iid(output)
                    self.finish(self.json_encode({'status':'success','message':'new image saved','data':output}))
                except:
                    # duplicated index error
                    self.dropError(409,'key violation')
        except:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data.')

    @asynchronous
    @coroutine
    def put(self, image_id=None):
        # update an image
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(Image)
        fields_allowed_to_be_update = ['is_deleted','image_set_id',
        'is_public','url','image_type','trashed']
        if 'image_set_id' in self.input_data.keys():
            imgiid = self.input_data['image_set_id']
            imgset = yield self.settings['db'].imagesets.find_one({'iid':imgiid,'trashed':False})
            if imgset:
                update_data['image_set_iid'] = imgiid
            else:
                self.dropError(409,"image set referenced doesn't exist")
                return
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if image_id and update_ok:
            query = self.query_id(image_id)
            if 'trashed' in update_data.keys():
                del query['trashed']
            updobj = yield Image.objects.filter(**query).limit(1).find_all()
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
                self.dropError(404,'image not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    def delete(self, image_id=None):
        # delete an image
        if image_id:
            query = self.query_id(image_id)
            updobj = yield self.settings['db'].images.find_one(query)
            if updobj:
                # check for references
                refcount = 0
                iid = updobj['image_set_iid']
                try:
                    updobj = yield self.settings['db'].images.update(query,{'$set':{'trashed':True,'updated_at':datetime.now()}})
                    self.setSuccess(200,'image successfully deleted')
                except:
                    self.dropError(500,'fail to delete image')
            else:
                self.dropError(404,'image not found')
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

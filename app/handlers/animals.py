#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine,engine,Task
from handlers.base import BaseHandler
from models.animal import Animal
from tornado.escape import utf8
from datetime import datetime,time

class AnimalsHandler(BaseHandler):
    """A class that handles requests about animals informartion
    """

    def query_id(self,animal_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(animal_id) }
        except:
            try:
                query = { 'id' : ObjId(animal_id) }
            except:
                query = { 'name' : animal_id}
        query['trashed'] = trashed
        return query

    @asynchronous
    @coroutine
    def get(self, animal_id=None):
        trashed = self.get_argument('trashed',False)
        if trashed:
            if trashed.lower() == 'true':
                trashed = True
            else:
                trashed = False
        if animal_id:
            if animal_id == 'list':
                objs = yield self.settings['db'][self.settings['animals']].find({'trashed':trashed}).to_list(None)
                orgs = yield self.settings['db'].organizations.find({'trashed':trashed}).to_list(None)
                orgnames = dict()
                for org in orgs:
                    orgnames[org['iid']] = org['name']
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs,orgnames)}))
            else:
                # return a specific animal accepting as id the integer id, hash and name
                query = self.query_id(animal_id)
                Animals = Animal()
                Animals.set_collection(self.settings['animals'])
                objs = yield Animals.objects.filter(**query).limit(1).find_all()
                if len(objs) > 0:
                    objanimal = yield Task(self.prepareOutput,objs[0].to_son(),trashed)
                    self.set_status(200)
                    self.finish(self.json_encode(objanimal))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            # return a list of animals
            queryfilter = {'trashed':trashed }
            filtersaccepted = ['gender','organization_id','dob_start','dob_end']
            for k,v in self.request.arguments.items():
                if k in filtersaccepted:
                    queryfilter[k] = self.get_argument(k)
            if 'organization_id' in queryfilter.keys():
                queryfilter['owner_organization_iid'] = int(queryfilter['organization_id'])
                del queryfilter['organization_id']
            try:
                if 'dob_start' in queryfilter.keys() or 'dob_end' in queryfilter.keys():
                    queryfilter['date_of_birth'] = dict()
                    if 'dob_start' in queryfilter.keys():
                        queryfilter['date_of_birth']["$gte"] = datetime.combine(datetime.strptime(queryfilter['dob_start'], "%Y-%m-%d").date(),time.min)
                        del queryfilter['dob_start']
                    if 'dob_end' in queryfilter.keys():
                        queryfilter['date_of_birth']['$lte'] = datetime.combine(datetime.strptime(queryfilter['dob_end'], "%Y-%m-%d").date(),time.min)
                        del queryfilter['dob_end']
            except:
                self.dropError(400,'invalid value for dob_start/dob_end')
                return
            noimages = self.get_argument('no_images','')
            if noimages.lower() == 'true':
                noimages = True
            else:
                noimages = False
            print(noimages)
            objs = yield self.settings['db'].imagesets.find(queryfilter).to_list(None)
            iids = [x['animal_iid'] for x in objs]
            objs = yield self.settings['db'][self.settings['animals']].find({'iid': { '$in' : iids }}).to_list(None)
            output = list()
            apiout = self.get_argument('api',None)
            for x in objs:
                if apiout:
                    obj = dict(x)
                    obj['obj_id'] = str(x['_id'])
                    del obj['_id']
                    obj['organization_id'] = obj['organization_iid']
                    del obj['organization_iid']
                    obj['primary_image_set_id'] = obj['primary_image_set_iid']
                    del obj['primary_image_set_iid']
                    self.switch_iid(obj)
                else:
                    obj = yield Task(self.prepareOutput,x,trashed,noimages)
                output.append(obj)
            self.set_status(200)
            if apiout:
                outshow = {'status':'success','data':output}
            else:
                outshow = output
            self.finish(self.json_encode(outshow))

    @asynchronous
    @engine
    def post(self):
        # create a new animal
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(Animal)
        Animals = Animal()
        Animals.set_collection(self.settings['animals'])
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,Animals.__collection__)
        # encrypt password
        newobj['encrypted_password'] = self.encryptPassword(self.input_data['password'])
        newobj['organization_iid'] = self.input_data['organization_id']
        #try:
        if True:
            newanimal = Animals(**newobj)
            if newanimal.validate():
                # the new object is valid, so try to save
                try:
                    newsaved = yield newanimal.save()
                    output = newsaved.to_son()
                    output['obj_id'] = str(newsaved._id)
                    self.switch_iid(output)
                    del output['encrypted_password']
                    self.finish(self.json_encode({'status':'success','message':'new '+self.settings['animal']+' saved','data':output}))
                except:
                    # duplicated index error
                    self.dropError(409,'key violation')
        #except:
        else:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data.')

    @asynchronous
    @coroutine
    def put(self, animal_id=None):
        # update an animal
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(Animal)
        Animals = Animal()
        Animals.set_collection(self.settings['animals'])
        fields_allowed_to_be_update = ['email','trashed','organization_iid','admin']
        if 'organization_id' in self.input_data.keys():
            update_data['organization_iid'] = self.input_data['organization_id']
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if animal_id and update_ok:
            query = self.query_id(animal_id)
            if 'trashed' in update_data.keys():
                del query['trashed']
            updobj = yield Animals.objects.filter(**query).limit(1).find_all()
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
                            del output['encrypted_password']
                            self.finish(self.json_encode({'status':'success','message':self.settings['animal']+' updated','data':output}))
                        except:
                            # duplicated index error
                            self.dropError(409,'duplicated name for '+self.settings['animal'])
                except:
                    # received data is invalid in some way
                    self.dropError(400,'Invalid input data.')
            else:
                self.dropError(404,self.settings['animal']+' not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    def delete(self, animal_id=None):
        # delete an animal
        if animal_id:
            query = self.query_id(animal_id)
            updobj = yield self.settings['db'][self.settings['animals']].find_one(query)
            if updobj:
                # check for references
                refcount = 0
                iid = updobj['iid']
                # imageset - uploading_user_iid
                imgsetrc = yield self.settings['db'].imagesets.find({'animal_iid':iid,'trashed':False}).count()
                refcount += imgsetrc
                if refcount > 0:
                    self.dropError(409,"the "+self.settings['animal']+" can't be deleted because it has references in the database.")
                else:
                    try:
                        updobj = yield self.settings['db'][self.settings['animals']].update(query,{'$set':{'trashed':True,'updated_at':datetime.now()}})
                        self.setSuccess(200,self.settings['animal']+' successfully deleted')
                    except:
                        self.dropError(500,'fail to delete '+self.settings['animal'])
            else:
                self.dropError(404,self.settings['animal']+' not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    def list(self,objs,orgnames):
        """ Implements the list output used for UI in the website
        """
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            obj['name'] = x['name']
            if orgnames and x['organization_iid'] in orgnames.keys():
                obj['organization'] = orgnames[x['organization_iid']]
            else:
                obj['organization'] = '-'
            output.append(obj)
        return output

    @asynchronous
    @engine
    def prepareOutput(self,objs,trashed=False,noimages=False,callback=None):
        objanimal = dict()
        objanimal['id'] = objs['iid']
        objanimal['name'] = objs['name']
        objanimal['organization_id'] = objs['organization_iid']
        objanimal['primary_image_set_id'] = objs['primary_image_set_iid']
        # Get imagesets for the animal
        imgsets = yield self.settings['db'].imagesets.find({'animal_iid':objanimal['id'],'trashed':trashed}).to_list(None)
        imgsets_output = list()
        for oimgst in imgsets:
            obj = dict()
            obj['id'] = oimgst['iid']
            obj['is_verified'] = oimgst['is_verified']
            obj['latitude'] = oimgst['location'][0][0]
            obj['longitude'] = oimgst['location'][0][1]
            obj['gender'] = oimgst['gender']
            if oimgst['date_of_birth']:
                obj['date_of_birth'] = oimgst['date_of_birth'].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                obj['date_of_birth'] = None
            obj['main_image_id'] = oimgst['main_image_iid']
            obj['uploading_organization_id'] = oimgst['uploading_organization_iid']
            obj['notes'] = oimgst['notes']
            obj['organization_id'] = oimgst['owner_organization_iid']
            obj['user_id'] = oimgst['uploading_user_iid']
            cvreq = yield self.settings['db'].cvrequests.find_one({'image_set_iid':oimgst['iid']})
            if cvreq:
                obj['has_cv_request'] = True
                cvres = yield self.settings['db'].cvresults.find_one({'cv_request_iid':cvreq['iid']})
                if cvres:
                    obj['has_cv_result'] = True
                else:
                    obj['has_cv_result'] = False
            else:
                obj['has_cv_request'] = False
                obj['has_cv_result'] = False
            if not noimages:
                images = yield self.settings['db'].images.find({'image_set_iid':oimgst['iid'],'trashed':trashed}).to_list(None)
                outimages = list()
                for image in images:
                    obji = dict()
                    obji['id'] = image['iid']
                    obji['image_type'] = image['image_type']
                    obji['is_public'] = image['is_public']
                    obji['thumbnail_url'] = ''
                    obji['main_url'] = ''
                    obji['url'] = ''
                    # This will be updated
                    #"thumbnail_url":"http://lion-guardians-production.s3.amazonaws.com/2015/05/31/16/17/59/133/uploads_2Fe3f10f18_d176_41a7_84b9_0b2c5fef81e7_2F38yrs_Sikiria_300x300.jpg",
                    #"main_url":"http://lion-guardians-production.s3.amazonaws.com/2015/05/31/16/18/00/752/uploads_2Fe3f10f18_d176_41a7_84b9_0b2c5fef81e7_2F38yrs_Sikiria_300x300.jpg",
                    #"url":"http://lion-guardians-production.s3.amazonaws.com/2015/05/31/16/17/59/608/uploads_2Fe3f10f18_d176_41a7_84b9_0b2c5fef81e7_2F38yrs_Sikiria_300x300.jpg"
                    outimages.append(obji)
                #oimgst['_embedded'] = {'images':images}
                obj['_embedded'] = {'images':outimages}
            imgsets_output.append(obj)
        objanimal['_embedded'] = {'image_sets': imgsets_output}
        callback(objanimal)

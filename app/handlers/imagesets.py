#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine,Task,engine
from handlers.base import BaseHandler
from models.organization import Organization
from models.animal import Animal
from models.imageset import ImageSet,Image
from models.cv import CVRequest,CVResult
from bson import ObjectId as ObjId
from datetime import datetime
from json import dumps
from tornado.escape import json_decode
from schematics.exceptions import ValidationError
from lib.rolecheck import allowedRole, refusedRole, api_authenticated
from logging import info

class ImageSetsHandler(BaseHandler):
    """A class that handles requests about image sets informartion
    """

    def query_id(self,imageset_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(imageset_id) }
        except:
            try:
                query = { '_id' : ObjId(imageset_id) }
            except:
                self.dropError(400,'invalid id key')
                return
        query['trashed'] = trashed
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, imageset_id=None, param=None):
        if param == 'cvrequest':
            self.dropError(400,'to request cv identification you must use POST method')
            return
        trashed = self.get_argument('trashed',False)
        if trashed:
            if trashed == '*':
                trashed = { '$in' : [True,False] }
            else:
                trashed = (trashed.lower() == 'true')
        if imageset_id == 'list':
            # Show a list for the website
            # Get imagesets from the DB
            output = yield Task(self.list,trashed)
            self.setSuccess(200,'imagesets list',output)
        elif imageset_id and param == 'profile':
            query = self.query_id(imageset_id,trashed)
            imgset = yield self.settings['db'].imagesets.find_one(query)
            if imgset:
                imgprim = yield self.settings['db'][self.settings['animals']].find({},{'primary_image_set_iid':1}).to_list(None)
                imgprim = [x['primary_image_set_iid'] for x in imgprim]
                output = imgset
                output['obj_id'] = str(imgset['_id'])
                del output['_id']
                self.switch_iid(output)
                # Get organization name
                org = yield self.settings['db'].organizations.find_one({'iid':output['owner_organization_iid']})
                if org:
                    output['organization'] = org['name']
                    output['organization_id'] = org['iid']
                else:
                    output['organization'] = '-'
                    output['organization_id'] = '-'

                # Check animal
                if output['id'] in imgprim:
                    #it's a primary image set
                    output['is_primary'] = True
                    queryani = {'primary_image_set_iid':output['id']}
                else:
                    output['is_primary'] = False
                    queryani = {'iid':output['animal_iid']}
                animalobj = yield self.settings['db'][self.settings['animals']].find_one(queryani)
                if animalobj:
                    output['name'] = animalobj['name']
                else:
                    output['name'] = '-'

                if 'date_of_birth' in output.keys() and output['date_of_birth']:
                    output['age'] = str(self.age(output['date_of_birth']))
                else:
                    output['age'] = '-'

                #output['organization_id'] = output['organization_iid']
                #del output['organization_iid']
                output['uploading_organization_id'] = output['uploading_user_iid']
                del output['uploading_user_iid']
                output['uploading_organization_id'] = output['uploading_organization_iid']
                del output['uploading_organization_iid']
                output['owner_organization_id'] = output['owner_organization_iid']
                del output['owner_organization_iid']
                output['main_image_id'] = output['main_image_iid']
                del output['main_image_iid']

                # Get image
                img = yield self.settings['db'].images.find_one({'iid':output['main_image_id']})
                if img:
                    output['image'] = self.settings['S3_URL'] + img['url'] + '_thumbnail.jpg'
                else:
                    output['image'] = ''

                if output['location']:
                    output['latitude'] = output['location'][0][0]
                    output['longitude'] = output['location'][0][1]
                else:
                    output['latitude'] = None
                    output['longitude'] = None
                del output['location']

                # Getting cvrequest for this imageset
                print(output['id'])
                cvreq = yield self.settings['db'].cvrequests.find_one({'image_set_iid':output['id']})
                print(cvreq)
                if cvreq:
                    output['cvrequest'] = str(cvreq['_id'])
                    output['req_status'] = cvreq['status']
                    cvres = yield self.settings['db'].cvresults.find_one({'cvrequest_iid':cvreq['iid']})
                    if cvres:
                        output['cvresults'] = str(cvres['_id'])
                    else:
                        output['cvresults'] = None
                else:
                    output['req_status'] = None
                    output['cvrequest'] = None
                    output['cvresults'] = None

                output[self.settings['animal']+'_id'] = output['animal_iid']
                del output['animal_iid']

                self.setSuccess(200,'imageset found',output)
                return
            else:
                self.dropError(404,'imageset not found')
                return
        elif imageset_id and param == 'gallery':
            query = self.query_id(imageset_id,trashed)
            objimgset = yield self.settings['db'].imagesets.find_one(query)
            if objimgset:
                images = yield self.settings['db'].images.find({'image_set_iid':objimgset['iid'],'trashed':trashed}).to_list(None)
                output = dict()
                output['id'] = imageset_id
                cover = objimgset['main_image_iid']
                output['images'] = list()
                for img in images:
                    imgout = {'id':img['iid'],'type':img['image_type'],'is_public':img['is_public']}
                    for suf in ['_icon.jpg','_medium.jpg','_thumbnail.jpg']:
                        imgout[suf[1:-4]] = self.settings['S3_URL'] + img['url'] + suf
                    imgout['cover'] = (img['iid'] == cover)
                    output['images'].append(imgout)
                self.setSuccess(200,'gallery images for the image set '+str(imageset_id),output)
            else:
                self.dropError(404,'imageset not found')
            return
        else:
            if imageset_id:
                query = self.query_id(imageset_id,trashed)
                objimgsets = yield self.settings['db'].imagesets.find(query).to_list(None)
            else:
                objimgsets = yield self.settings['db'].imagesets.find({'trashed':trashed}).to_list(None)
            if len(objimgsets) > 0:
                loutput = list()
                for objimgset in objimgsets:
                    output = dict(objimgset)
                    output['id'] = objimgset['iid']
                    del output['iid']
                    output['uploading_user_id'] = objimgset['uploading_user_iid']
                    del output['uploading_user_iid']
                    output['owner_organization_id'] = objimgset['owner_organization_iid']
                    del output['owner_organization_iid']
                    output['uploading_organization_id'] = objimgset['uploading_organization_iid']
                    del output['uploading_organization_iid']
                    if objimgset['location']:
                        output['latitude'] = objimgset['location'][0][0]
                        output['longitude'] = objimgset['location'][0][1]
                    else:
                        output['latitude'] = None
                        output['longitude'] = None
                    del output['location']
                    output['obj_id'] = str(objimgset['_id'])
                    del output['_id']
                    output[self.settings['animal']+'_id'] = objimgset['animal_iid']
                    del output['animal_iid']
                    output['main_image_id'] = objimgset['main_image_iid']
                    del output['main_image_iid']
                    loutput.append(output)
                self.set_status(200)
                if imageset_id:
                    loutput = loutput[0]
                self.finish(self.json_encode({'status':'success','data':loutput}))
            else:
                self.dropError(404,'imageset id not found')

    @asynchronous
    @coroutine
    @api_authenticated
    def post(self, imageset_id=None, cvrequest=None):
        if not imageset_id:
            # create a new imageset or new cvrequest
            # parse data recept by POST and get only fields of the object
            newobj = self.parseInput(ImageSet)
            # getting new integer id
            newobj['iid'] = yield Task(self.new_iid,ImageSet.collection())
            dt = datetime.now()
            newobj['created_at'] = dt
            newobj['updated_at'] = dt
            newobj['trashed'] = False
            # validate the input
            fields_needed = ['uploading_user_id','uploading_organization_id','owner_organization_id',
                             'is_verified','gender','date_of_birth',
                             'tags','date_stamp','notes',self.settings['animal']+'_id','main_image_id']
            keys = list(self.input_data.keys())
            for field in fields_needed:
                if field not in keys:
                    self.dropError(400,'you must provide the key for '+field+' even it has the value = null')
                    return
            # check if date_stamp are valid
            if newobj['date_stamp']:
                try:
                    dts = datetime.strptime(newobj['date_stamp'], "%Y-%m-%d").date()
                    newobj['date_stamp'] = str(dts)
                except:
                    self.dropError(400,'invalid date_stamp. you must provide it in format YYYY-MM-DD')
                    return
            if newobj['date_of_birth']:
                try:
                    newobj['date_of_birth'] = datetime.strptime(newobj['date_of_birth'], "%Y-%m-%d")
                except:
                    self.dropError(400,'invalid date_of_birth. you must provide it in format YYYY-MM-DD')
                    return
            # check if user exists
            useriid = self.input_data['uploading_user_id']
            userexists = yield self.settings['db'].users.find_one({'iid':useriid,'trashed':False})
            if userexists:
                newobj['uploading_user_iid'] = useriid
            else:
                self.dropError(409,"uploading user id referenced doesn't exist")
                return
            # check if organizations exists
            orgiid = self.input_data['uploading_organization_id']
            orgexists = yield self.settings['db'].organizations.find_one({'iid':orgiid,'trashed':False})
            if orgexists:
                newobj['uploading_organization_iid'] = orgiid
            else:
                self.dropError(409,"uploading organization id referenced doesn't exist")
                return
            oorgiid = self.input_data['owner_organization_id']
            oorgexists = yield self.settings['db'].organizations.find_one({'iid':oorgiid,'trashed':False})
            if oorgexists['iid'] == orgiid:
                newobj['owner_organization_iid'] = oorgiid
            else:
                self.dropError(409,"owner organization id referenced doesn't exist")
                return
            if 'latitude' in self.input_data.keys() and self.input_data['latitude'] and \
              'longitude' in self.input_data.keys() and self.input_data['longitude']:
              newobj['location'] = [[self.input_data['latitude'],self.input_data['longitude']]]
            newobj['animal_iid'] = self.input_data[self.settings['animal']+'_id']
            try:
                newimgset = ImageSet(newobj)
                newimgset.validate()

                newobj = yield self.settings['db'].imagesets.insert(newimgset.to_native())
                output = newimgset.to_native()
                self.switch_iid(output)
                output['obj_id'] = str(newobj)
                output['owner_organization_id'] = output['owner_organization_iid']
                del output['owner_organization_iid']
                output['uploading_organization_id'] = output['uploading_organization_iid']
                del output['uploading_organization_iid']
                output['uploading_user_id'] = output['uploading_user_iid']
                del output['uploading_user_iid']
                output['main_image_id'] = output['main_image_iid']
                del output['main_image_iid']
                output[self.settings['animal']+'_id'] = output['animal_iid']
                del output['animal_iid']

                self.set_status(200)
                self.finish(self.json_encode({'status':'success','message':'new image set added','data':output}))
            except ValidationError, e:
                self.dropError(400,"Invalid input data. Error: "+str(e))
                return
        else:
            query = self.query_id(imageset_id)
            imgchk = yield self.settings['db'].imagesets.find_one(query)
            if imgchk:
                cvreqchk = yield self.settings['db'].cvrequests.find_one({'image_set_iid':imgchk['iid']})
                if cvreqchk:
                    self.dropError(400,'a request for indentification of this imageset already exists in the database')
                    return
                if not self.settings['animals'] in self.input_data.keys():
                    self.dropError(400,'the cvrequest needs a list of '+self.settings['animals']+' id like: { "'+self.settings['animals']+'" : [<id>,...] }')
                    return
                if cvrequest:
                    # Send a request for identification in the CV Server
                    if imgchk['date_of_birth']:
                        age = self.age(imgchk['date_of_birth'])
                    else:
                        age = None
                    body = {"identification":
                        {"images": list(),
                        "gender": imgchk['gender'],
                        "age": age,
                        self.settings['animals'] : list()
                        }
                    }
                    query_images = {'image_set_iid':imgchk['iid']}
                    imgs = yield self.settings['db'].images.find(query_images).to_list(None)
                    limgs = list()
                    for img in imgs:
                        limgs.append({'id':img['iid'],'type':img['image_type'],'url':self.settings['S3_URL']+img['url']+'_full.jpg'})
                    animals = self.input_data[self.settings['animals']]
                    animalscheck = yield self.settings['db'][self.settings['animals']].find({'iid' : { '$in' : animals }}).to_list(None)
                    if not animalscheck:
                        self.dropError(400,'no id valid in the list of '+self.settings['animals']+' passed')
                        return
                    lanimals = list()
                    for animal in animalscheck:
                        url = self.settings['url']+self.settings['animals']+'/'
                        lanimals.append({'id':animal['iid'],'url':url+str(animal['iid'])})
                    body['identification']['images'] = limgs
                    body['identification'][self.settings['animals']] = lanimals
                    sbody = dumps(body)
                    #print(sbody)
                    try:
                        response = yield Task(self.api,url=self.settings['CVSERVER_URL_IDENTIFICATION'],method='POST', \
                                            body=sbody,auth_username=self.settings['CV_USERNAME'],auth_password=self.settings['CV_PASSWORD'])
                        rbody = json_decode(response.body)
                        # Create a cvrequest mongodb object for this ImageSet
                        newobj = dict()
                        newobj['iid'] = yield Task(self.new_iid,CVRequest.collection())
                        # This will be get from the user that do the request
                        newobj['requesting_organization_iid'] = self.current_user['org_id']
                        newobj['image_set_iid'] = imageset_id
                        newobj['status'] = rbody['status']
                        newobj['server_uuid'] = rbody['id']
                        newobj['request_body'] = sbody
                        newsaved = CVRequest(newobj)
                        newsaved.validate()
                        newreqadd = yield self.settings['db'].cvrequests.insert(newsaved.to_native())
                        output = newsaved.to_native()
                        output['obj_id'] = str(newreqadd)
                        self.switch_iid(output)
                        del output['request_body']
                        output['requesting_organization_id'] = output['requesting_organization_iid']
                        del output['requesting_organization_iid']
                        output['image_set_id'] = output['image_set_iid']
                        del output['image_set_iid']
                        self.set_status(response.code)
                        self.finish(self.json_encode({'status':'success','message':response.reason,'data':output}))
                    except ValidationError, e:
                        self.set_status(500)
                        self.finish({'status':'error','message':'Fail to execute the request for identification. Errors: '+str(e)})
                else:
                    self.dropError(400,'bad request')
            else:
                self.dropError(404,'imageset id not found')

    @asynchronous
    @coroutine
    @api_authenticated
    def put(self, imageset_id=None):
        # update an imageset
        if imageset_id:
            # getting the object
            query = self.query_id(imageset_id)
            del query['trashed']
            objimgset = yield self.settings['db'].imagesets.find_one(query)
            if objimgset:
                dt = datetime.now()
                objimgset['updated_at'] = dt
                # validate the input
                fields_allowed = ['uploading_user_id','uploading_organization_id','owner_organization_id',
                                 'is_verified','latitude','longitude','gender','date_of_birth',
                                 'tags','date_stamp','notes',self.settings['animal']+'_id','main_image_id','trashed']
                update_data = dict()
                for k,v in self.input_data.items():
                    if k in fields_allowed:
                        update_data[k] = v
                for field in fields_allowed:
                    if field in update_data.keys():
                        if field in ['uploading_user_id','uploading_organization_id','owner_organization_id',\
                                    self.settings['animal']+'_id','main_image_id']:
                            vkey = field.index('_id')
                            vkey = field[:vkey]+'_iid'
                            cmd = "objimgset['"+vkey+"'] = "+str(update_data[field])
                            exec(cmd)
                            if vkey == self.settings['animal']+'_iid':
                                objimgset['animal_iid'] = update_data[self.settings['animal']+'_id']
                                del objimgset[self.settings['animal']+'_iid']
                            del update_data[field]
                            continue
                        elif field in ['date_stamp','date_of_birth']:
                            # check if date_stamp are valid
                            if update_data[field]:
                                try:
                                    dts = datetime.strptime(update_data[field], "%Y-%m-%d")
                                    print(dts)
                                    if field == 'date_stamp':
                                        objimgset['date_stamp'] = str(dts.date())
                                        continue
                                    else:
                                        objimgset['date_of_birth'] = dts
                                        continue
                                except:
                                    self.dropError(400,'invalid '+field)
                                    return
                        elif field in ['latitude','longitude']:
                            if 'latitude' in update_data.keys() and update_data['latitude'] and \
                               'longitude' in update_data.keys() and update_data['longitude']:
                                print(update_data[field])
                                objimgset['location'] = [[0,0]]
                                objimgset['location'][0][0] = float(update_data['latitude'])
                                objimgset['location'][0][1] = float(update_data['longitude'])
                                del update_data['latitude']
                                del update_data['longitude']
                            else:
                                objimgset['location'] = None
                            continue
                        elif field == 'trashed':
                            objimgset['trashed'] = update_data[field]
                            continue
                        objimgset[field] = update_data[field]

                # check if user exists
                useriid = objimgset['uploading_user_iid']
                userexists = yield self.settings['db'].users.find_one({'iid':useriid,'trashed':False})
                if not userexists:
                    self.dropError(409,"uploading user id referenced doesn't exist")
                    return
                # check if organizations exists
                orgiid = objimgset['uploading_organization_iid']
                orgexists = yield self.settings['db'].organizations.find_one({'iid':orgiid,'trashed':False})
                if not orgexists:
                    self.dropError(409,"uploading organization id referenced doesn't exist")
                    return
                oorgiid = objimgset['owner_organization_iid']
                oorgexists = yield self.settings['db'].organizations.find_one({'iid':oorgiid,'trashed':False})
                if oorgexists['iid'] != oorgiid:
                    self.dropError(409,"owner organization id referenced doesn't exist")
                    return
                if objimgset['animal_iid']:
                    aniexists = yield self.settings['db'][self.settings['animals']].find_one({'iid':objimgset['animal_iid'],'trashed':False})
                    if aniexists['iid'] != objimgset['animal_iid']:
                        self.dropError(409,'the '+self.settings['animal']+" id sent doesn't exist")
                        return
                try:
                    imgid = ObjId(objimgset['_id'])
                    del objimgset['_id']
                    print(objimgset)
                    objimgset = ImageSet(objimgset)
                    objimgset.validate()
                    objimgset = objimgset.to_native()
                    #objimgset['_id'] = imgid
                    updnobj = yield self.settings['db'].imagesets.update({'_id':imgid},{'$set' : objimgset},upsert=True)
                    print(updnobj)
                    output = objimgset
                    self.switch_iid(output)
                    output['obj_id'] = str(imgid)
                    output['owner_organization_id'] = output['owner_organization_iid']
                    del output['owner_organization_iid']
                    output['uploading_organization_id'] = output['uploading_organization_iid']
                    del output['uploading_organization_iid']
                    output['uploading_user_id'] = output['uploading_user_iid']
                    del output['uploading_user_iid']
                    output['main_image_id'] = output['main_image_iid']
                    del output['main_image_iid']
                    output[self.settings['animal']+'_id'] = output['animal_iid']
                    del output['animal_iid']

                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','message':'image set updated','data':output}))
                except ValidationError, e:
                    self.dropError(400,"Invalid input data. Error: "+str(e))
                    return
            else:
                self.dropError(404,'imageset id not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, imageset_id=None):
        self.s3con = self.initS3()
        if not self.s3con:
            self.dropError(500,'Unable to connect in S3.')
            return
        # delete an imageset
        if imageset_id:
            query = self.query_id(imageset_id)
            query['trashed'] = {'$in':[True,False]}
            imgobj = yield self.settings['db'].imagesets.find_one(query)
            if imgobj:
                # 1 - Remove imaget set
                rmved = yield self.settings['db'].imagesets.remove({'iid':imgobj['iid']})
                print rmved
                # 2 - Remove images of the image set
                imgl = yield self.settings['db'].images.find({'image_set_iid':imgobj['iid']}).to_list(None)
                for img in imgl:
                    # Delete the source file
                    srcurl = self.settings['S3_FOLDER'] + '/imageset_'+str(imgobj['iid'])+'_'+str(imgobj['_id'])+'/'
                    srcurl = srcurl + img['created_at'].date().isoformat() + '_image_'+str(img['iid'])+'_'+str(img['_id'])
                    try:
                        for suf in ['_full.jpg','_icon.jpg','_medium.jpg','_thumbnail.jpg']:
                            self.s3con.delete(srcurl+suf,self.settings['S3_BUCKET'])
                    except Exception, e:
                        self.setSuccess(500,'Fail to delete image in S3. Errors: '+str(e))
                        return
                rmved = yield self.settings['db'].images.remove({'image_set_iid':imgobj['iid']},multi=True)
                print rmved
                # 3 - Removing cvrequests and cvresults
                cvreql = yield self.settings['db'].cvrequests.find({'image_set_iid':imgobj['iid']}).to_list(None)
                for cvreq in cvreql:
                    # Removing cvresult
                    rmved = yield self.settings['db'].cvresults.remove({'cvrequest_iid':cvreq['iid']})
                    print rmved
                    # Removing cvrequest
                    rmved = yield self.settings['db'].cvrequests.remove({'_id':cvreq['_id']})
                    print rmved
            else:
                self.dropError(404,'image set not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    @asynchronous
    @engine
    def list(self,trashed,callback=None):
        objs_imgsets = yield self.settings['db'].imagesets.find({'trashed':trashed}).to_list(None)
        animals = yield self.settings['db'][self.settings['animals']].find({'trashed':trashed}).to_list(None)
        primary_imgsets_list = list()
        animals_names = dict()
        for x in animals:
            animals_names[x['iid']] = x['name']
            if x['primary_image_set_iid']:
                primary_imgsets_list.append(x['primary_image_set_iid'])
        output = list()
        for obj in objs_imgsets:
            imgset_obj = dict()
            imgset_obj['obj_id'] = str(obj['_id'])
            imgset_obj['id'] = obj['iid']

            if obj['animal_iid']:
                imgset_obj['name'] = animals_names[obj['animal_iid']]
                imgset_obj[self.settings['animal']+'_id'] = obj['animal_iid']
            else:
                imgset_obj['name'] = '-'
                imgset_obj[self.settings['animal']+'_id'] = None

            obji = yield self.settings['db'].images.find_one({'iid':obj['main_image_iid']})
            if obji:
                imgset_obj['thumbnail'] = self.settings['S3_URL']+obji['url']+'_icon.jpg'
                imgset_obj['image'] = self.settings['S3_URL']+obji['url']+'_medium.jpg'
            else:
                obji = yield self.settings['db'].images.find({'image_set_iid':obj['iid'],'trashed':trashed}).to_list(None)
                if len(obji) > 0:
                    imgset_obj['thumbnail'] = self.settings['S3_URL']+obji[0]['url']+'_icon.jpg'
                    imgset_obj['image'] = self.settings['S3_URL']+obji[0]['url']+'_medium.jpg'
                else:
                    imgset_obj['thumbnail'] = ''
                    imgset_obj['image'] = ''

            if obj['date_of_birth']:
                imgset_obj['age'] = self.age(born=obj['date_of_birth'])
            else:
                imgset_obj['age'] = '-'

            if obj['date_stamp']:
                imgset_obj['date_stamp'] = obj['date_stamp']
            else:
                imgset_obj['date_stamp'] = '-'

            if obj['tags']:
                imgset_obj['tags'] = obj['tags']
            else:
                imgset_obj['tags'] = None

            if obj['owner_organization_iid']:
                objo = yield self.settings['db'].organizations.find_one({'iid':obj['owner_organization_iid'],'trashed':trashed})
                if objo:
                    imgset_obj['organization'] = objo['name']
                    imgset_obj['organization_id'] = obj['owner_organization_iid']
                else:
                    imgset_obj['organization'] = '-'
                    imgset_obj['organization_id'] = '-'

            imgset_obj['gender'] = obj['gender']
            imgset_obj['is_verified'] = obj['is_verified']
            imgset_obj['is_primary'] = (obj['iid'] in primary_imgsets_list)

            objcvreq = yield self.settings['db'].cvrequests.find_one({'image_set_iid':obj['iid']})
            if objcvreq:
                imgset_obj['cvrequest'] = str(objcvreq['_id'])
                imgset_obj['req_status'] = objcvreq['status']
            else:
                imgset_obj['cvrequest'] = None
                imgset_obj['req_status'] = None

            imgset_obj['cvresults'] = None
            if objcvreq:
                objcvres = yield self.settings['db'].cvresults.find_one({'cvrequest_iid':objcvreq['iid']})
                if objcvres:
                    imgset_obj['cvresults'] = str(objcvres['_id'])
            output.append(imgset_obj)
        callback(output)

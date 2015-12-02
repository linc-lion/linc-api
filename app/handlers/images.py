#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.imageset import Image
from bson import ObjectId as ObjId
from datetime import datetime
from schematics.exceptions import ValidationError
from tinys3 import Connection as s3con
from os.path import realpath,dirname
from lib.image_utils import generate_images
from os import remove
from lib.rolecheck import allowedRole, refusedRole, api_authenticated
import logging

class ImagesHandler(BaseHandler):
    """A class that handles requests about images informartion
    """
    def initialize(self):
        S3_ACCESS_KEY = self.settings['S3_ACCESS_KEY']
        S3_SECRET_KEY = self.settings['S3_SECRET_KEY']
        S3_BUCKET = self.settings['S3_BUCKET']
        try:
            self.s3con = s3con(S3_ACCESS_KEY,S3_SECRET_KEY,default_bucket=S3_BUCKET)
        except:
            self.s3con = None
            print('\n\nFail to connect to S3')

    def query_id(self,image_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(image_id) }
        except:
            try:
                query = { '_id' : ObjId(image_id) }
            except:
                self.dropError(400,'invalid id key')
                return
        query['trashed'] = trashed
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, image_id=None):
        download = self.get_argument('download',None)
        if download:
            dimg = [int(x) for x in download.split(',')]
            limgs = yield self.settings['db'].images.find({'iid' : {'$in' : dimg}}).to_list(None)
            if len(limgs) > 0:
                s3url = self.settings['S3_URL']
                suf = '_full.jpg'
                urls = [ s3url+x['url']+suf for x in limgs]
                self.setSuccess(200,'links for the requested images with id='+download,urls)
                return
            else:
                self.dropError(400,"you need to pass image's ids separated by commas")
                return
        else:
            trashed = self.get_argument('trashed',False)
            if trashed:
                if trashed == '*':
                    trashed = { '$in' : [True,False] }
                else:
                    trashed = (trashed.lower() == 'true')
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
                    objs = yield self.settings['db'].images.find_one(query)
                    if objs:
                        objimage = objs
                        self.switch_iid(objimage)
                        #objimage['id'] = objs['iid']
                        objimage['obj_id'] = str(objs['_id'])
                        #del objimage['iid']
                        del objimage['_id']
                        objimage['image_set_id'] = objimage['image_set_iid']
                        del objimage['image_set_iid']
                        objimage['url'] = self.imgurl(objimage['url'],'medium')

                        self.set_status(200)
                        self.finish(self.json_encode({'status':'success','data':objimage}))
                    else:
                        self.set_status(404)
                        self.finish(self.json_encode({'status':'error','message':'not found'}))
            else:
                # return a list of images
                objs = yield self.settings['db'].images.find({'trashed':trashed}).to_list(None)
                output = list()
                for x in objs:
                    obj = dict(x)
                    obj['obj_id'] = str(x['_id'])
                    del obj['_id']
                    self.switch_iid(obj)
                    obj['image_set_id'] = obj['image_set_iid']
                    del obj['image_set_iid']
                    obj['url'] = self.imgurl(obj['url'],'medium')
                    output.append(obj)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':output}))

    @asynchronous
    @engine
    @api_authenticated
    def post(self,updopt=None):
        # create a new image
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(Image)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,Image.collection())
        # prepare new obj
        dt = datetime.now()
        newobj['created_at'] = dt
        newobj['updated_at'] = dt
        fields_needed = ['image_set_id',
        'is_public','image_type']
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
            folder_name = 'imageset_'+str(isexists['iid'])+'_'+str(isexists['_id'])
            url = folder_name+'/'+dt.date().isoformat() + '_image_' + str(newobj['iid']) + '_'
            newobj['url'] = url
            print(newobj)
            newimage = Image(newobj)
            newimage.validate()
            # the new object is valid, so try to save
            if updopt and not self.s3con:
                self.dropError(500,'Fail to connect to S3 to save the files. You must request support.')
                return
            try:
                newsaved = yield self.settings['db'].images.insert(newimage.to_native())
                updurl = yield self.settings['db'].images.update({'_id':newsaved},{'$set' : {'url':url+str(newsaved)}})
                output = newimage.to_native()
                # if upload file activated, generate files and upload to s3
                if updopt:
                    #print(self.settings['S3_ACCESS_KEY'])
                    #print(self.settings['S3_SECRET_KEY'])
                    if 'image' in self.input_data.keys():
                        fupdname = dt.date().isoformat() + '_image_' + str(newobj['iid']) + '_' + str(newsaved)
                        imgname = fupdname + '.img'
                        dirfs = dirname(realpath(__file__))
                        fh = open(dirfs+'/'+imgname, 'wb')
                        fh.write(self.input_data['image'].decode('base64'))
                        fh.close()
                        generate_images(dirfs+'/'+imgname)
                        from datetime import timedelta
                        t = timedelta(days=1)
                        for suf in ['_full.jpg','_icon.jpg','_medium.jpg','_thumbnail.jpg']:
                            keynames3 = self.settings['S3_FOLDER'] + '/' + folder_name + '/' + fupdname + suf
                            print(keynames3)
                            f = open(dirfs+'/'+imgname[:-4]+suf,'rb')
                            self.s3con.upload(keynames3,f,expires=t,content_type='image/jpeg',public=True)
                            f.close()
                            remove(dirfs+'/'+imgname[:-4]+suf)
                    else:
                        self.dropError(400,'upload resource was used but no file can be found in the request. You must convert the file to base64 and pass it in the "image" key in the body JSON data.')
                        return

                output['obj_id'] = str(newsaved)
                output['url'] = url+str(newsaved)
                output['image_set_id'] = output['image_set_iid']
                del output['image_set_iid']
                self.switch_iid(output)
                #self.finish(self.json_encode({'status':'success','message':'new image saved','data':output}))
                self.setSuccess(201,'new image saved',output)
            except ValidationError,e:
                # duplicated index error
                self.dropError(409,'fail to save image. Error: '+str(e))
        except ValidationError, e:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data. Error: '+str(e))

    @asynchronous
    @coroutine
    @api_authenticated
    def put(self, image_id=None):
        # update an image
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(Image)
        fields_allowed_to_be_update = ['image_set_id',
        'is_public','image_type','trashed']
        if 'image_set_id' in self.input_data.keys():
            imgiid = self.input_data['image_set_id']
            imgset = yield self.settings['db'].imagesets.find_one({'iid':imgiid,'trashed':False})
            if imgset:
                update_data['image_set_id'] = imgiid
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
            updobj = yield self.settings['db'].images.find_one(query)
            updurl = False
            if updobj:
                for field in fields_allowed_to_be_update:
                    if field == 'image_set_id' and field in update_data.keys():
                        orig_imgset_id = updobj['image_set_iid']
                        updobj['image_set_iid'] = update_data['image_set_id']
                        updurl = True
                    elif field in update_data.keys():
                        updobj[field] = update_data[field]
                dt = datetime.now()
                updobj['updated_at'] = dt
                try:
                    if updurl:
                        # The url will be changed since the imageset will be other
                        folder_name = 'imageset_'+str(imgset['iid'])+'_'+str(imgset['_id'])
                        url = folder_name+'/'+updobj['created_at'].date().isoformat() + '_image_' + str(updobj['iid']) + '_' + str(updobj['_id'])
                        # copy image
                        # No need to specify the target bucket if we're copying inside the same bucket
                        if not self.s3con:
                            self.dropError(500,'Fail to connect to S3')
                            return
                        oldimgset = yield self.settings['db'].imagesets.find_one({'iid':orig_imgset_id,'trashed':False})
                        srcurl = self.settings['S3_FOLDER'] + '/imageset_'+str(oldimgset['iid'])+'_'+str(oldimgset['_id'])+'/'
                        srcurl = srcurl + updobj['created_at'].date().isoformat() + '_image_'+str(updobj['iid'])+'_'+str(updobj['_id'])
                        desurl = self.settings['S3_FOLDER'] + '/' + url
                    objupdid = ObjId(str(updobj['_id']))
                    del updobj['_id']
                    updobj = Image(updobj)
                    updobj.validate()
                    updobj = updobj.to_native()
                    # the object is valid, so try to save
                    try:
                        updobj['_id'] = objupdid
                        saved = yield self.settings['db'].images.update(query,updobj)
                        # Ok, data saved so operate s3
                        # Copy the image to the new imageset
                        # Copy the full for backup
                        output = updobj
                        output['obj_id'] = str(objupdid)
                        del output['_id']
                        # Change iid to id in the output
                        self.switch_iid(output)

                        if 'image_set_id' in self.input_data.keys() \
                            and updobj['image_set_iid'] != imgiid:
                            # image set was changed
                            try:
                                bkpcopy = self.settings['S3_FOLDER']+'/backup/'+updobj['created_at'].date().isoformat() + '_image_'+str(updobj['iid'])+'_'+str(updobj['_id'])
                            except:
                                pass
                            self.s3con.copy(srcurl+'_full.jpg',self.settings['S3_BUCKET'],bkpcopy+'_full.jpg')
                            for suf in ['_full.jpg','_icon.jpg','_medium.jpg','_thumbnail.jpg']:
                                # Copy the files
                                self.s3con.copy(srcurl+suf,self.settings['S3_BUCKET'],desurl+suf)
                                # Delete the source file
                                self.s3con.delete(srcurl+suf,self.settings['S3_BUCKET'])
                        output['image_set_id'] = output['image_set_iid']
                        del output['image_set_iid']

                        #self.finish(self.json_encode({'status':'success','message':'image updated','data':output}))
                        self.setSuccess(200,'image id '+str(output['id'])+ ' updated successfully.',output)
                    except Exception, e:
                        # duplicated index error
                        self.dropError(409,'key violation. Errors: '+str(e))
                except ValidationError, e:
                    # received data is invalid in some way
                    self.dropError(400,'Invalid input data. Errors: '+str(e))
            else:
                self.dropError(404,'image not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, image_id=None):
        # delete an image
        purge = self.get_argument('purge',None)
        if image_id:
            query = self.query_id(image_id)
            query['trashed'] = {'$in':[False,True]}
            updobj = yield self.settings['db'].images.find_one(query)
            if updobj:
                # check for references
                refcount = 0
                iid = updobj['image_set_iid']
                try:
                    print(updobj)
                    if not purge:
                        delobj = yield self.settings['db'].images.update(query,{'$set':{'trashed':True,'updated_at':datetime.now()}})
                        self.setSuccess(200,'image successfully deleted')
                    else:
                        delobj = yield self.settings['db'].images.remove(query)
                        # Purge was activated, so delete everything
                        # Delete the source file
                        bkpcopy = self.settings['S3_FOLDER']+'/backup/'+updobj['created_at'].date().isoformat() + '_image_'+str(updobj['iid'])+'_'+str(updobj['_id'])+'_full.jpg'
                        imgset = yield self.settings['db'].imagesets.find_one({'iid':updobj['image_set_iid']})
                        srcurl = self.settings['S3_FOLDER'] + '/imageset_'+str(imgset['iid'])+'_'+str(imgset['_id'])+'/'
                        srcurl = srcurl + updobj['created_at'].date().isoformat() + '_image_'+str(updobj['iid'])+'_'+str(updobj['_id'])
                        try:
                            self.s3con.delete(bkpcopy,self.settings['S3_BUCKET'])
                        except:
                            pass
                        try:
                            for suf in ['_full.jpg','_icon.jpg','_medium.jpg','_thumbnail.jpg']:
                                self.s3con.delete(srcurl+suf,self.settings['S3_BUCKET'])
                        except Exception, e:
                            self.setSuccess(200,'image successfully deleted but can\'t remove files from S3. Errors: '+str(e))
                            return
                        self.setSuccess(200,'image successfully deleted and purged')
                except Exception,e:
                    self.dropError(500,'fail to delete image. Errors: '+str(e))
            else:
                self.dropError(404,'image not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    def list(self,objs,callback=None):
        """ Implements the list output used for UI in the website
        """
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            url = self.imgurl(x['url'],'icon')
            obj['url'] = url
            output.append(obj)
        return output

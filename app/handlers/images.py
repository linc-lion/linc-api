#!/usr/bin/env python
# -*- coding: utf-8 -*-

# LINC is an open source shared database and facial recognition
# system that allows for collaboration in wildlife monitoring.
# Copyright (C) 2016  Wildlifeguardians
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information or to contact visit linclion.org or email tech@linclion.org

import os
from tornado.web import asynchronous
from tornado.gen import engine, coroutine, Task
from handlers.base import BaseHandler
from models.imageset import Image
from bson import ObjectId as ObjId
from datetime import datetime
from schematics.exceptions import ValidationError
from os.path import realpath, dirname, exists, splitext
from lib.image_utils import generate_images
from os import remove
from lib.rolecheck import api_authenticated
from logging import info
from uuid import uuid4
from hashlib import md5
from tornadoist import ProcessMixin
from base64 import b64decode
from json import dumps
from lib.upload_s3 import upload_to_s3, s3_copy, s3_delete

from functools import partial
from lib.voc_routines import process_voc
from concurrent.futures import ThreadPoolExecutor
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from tornado.httputil import HTTPHeaders


class ImagesHandler(BaseHandler, ProcessMixin):
    """A class that handles requests about images information."""
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')

    def initialize(self):
        super().initialize()
        self.process = False

    def on_finish(self):
        if self.request.method == 'POST' and self.process:
            fupdname = self.dt.date().isoformat() + '_image_' + self.imgid + '_' + self.imgobjid
            generate_images(self.imgname)
            for suf in ['_full.jpg', '_icon.jpg', '_medium.jpg', '_thumbnail.jpg']:
                keynames3 = self.settings['S3_FOLDER'] + '/' + self.folder_name + '/' + fupdname + suf
                info(str(keynames3))
                f = open(self.imgname[:-4] + suf, 'rb')
                # self.s3con.upload(keynames3,f,expires=t,content_type='image/jpeg',public=True)
                resp = upload_to_s3(self.settings['S3_ACCESS_KEY'], self.settings['S3_SECRET_KEY'], f, self.settings['S3_BUCKET'], keynames3)
                if resp:
                    info('File upload OK: ' + str(keynames3))
                else:
                    info('FAIL to upload: ' + str(keynames3))
                f.close()
                remove(self.imgname[:-4] + suf)

    def query_id(self, image_id):
        """The method configures the query that will find an object."""
        try:
            query = {'iid': int(image_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(image_id)}
            except Exception as e:
                self.response(400, 'Invalid id key. Error: ' + str(e) + '.')
                return
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, image_id=None):
        download = self.get_argument('download', None)
        if download:
            dimg = [int(x) for x in download.split(',')]
            limgs = yield self.Images.find({'iid': {'$in': dimg}}).to_list(None)
            if len(limgs) > 0:
                urls = list()
                for x in limgs:
                    iurl = self.imgurl(x['url'], 'full')
                    if 'filename' not in x.keys() or x['filename'] == '':
                        fname = 'imageset_' + str(x['image_set_iid']) + '_image_' + str(x['iid']) + '.jpg'
                    else:
                        fname = x['filename']
                    urls.append({'url': iurl, 'filename': fname})
                self.response(200, 'Links for the requested images with id=' + download + '.', urls)
                return
            else:
                self.response(404, "Image ids separated by commas are mandatory for this request.")
                return
        else:
            info(image_id)
            if image_id:
                if image_id == 'list':
                    objs = yield self.Images.find().skip(self.skip).limit(self.limit).to_list(None)
                    self.response(200, 'Images list.', self.list(objs))
                else:
                    # return a specific image accepting as id the integer id, hash and name
                    query = self.query_id(image_id)
                    info(query)
                    objs = yield self.Images.find_one(query)
                    if objs:
                        objimage = objs
                        self.switch_iid(objimage)
                        objimage['obj_id'] = str(objs['_id'])
                        del objimage['_id']
                        objimage['image_set_id'] = objimage['image_set_iid']
                        del objimage['image_set_iid']
                        objimage['url'] = self.imgurl(objimage['url'], 'medium')

                        self.set_status(200)
                        self.finish(self.json_encode({'status': 'success', 'data': objimage}))
                    else:
                        self.set_status(404)
                        self.finish(self.json_encode({'status': 'error', 'message': 'not found'}))
            else:
                # return a list of images
                objs = yield self.Images.find().skip(self.skip).limit(self.limit).to_list(None)
                output = list()
                for x in objs:
                    obj = dict(x)
                    obj['obj_id'] = str(x['_id'])
                    del obj['_id']
                    self.switch_iid(obj)
                    obj['image_set_id'] = obj['image_set_iid']
                    del obj['image_set_iid']
                    obj['url'] = self.imgurl(obj['url'], 'medium')
                    output.append(obj)
                self.set_status(200)
                # self.finish(self.json_encode({'status': 'success', 'message': 'Images list.', 'data': output}))
                # Pagination stats
                n_images = yield self.Images.count()
                stats = {'number_of_images': n_images, 'skip': self.skip, 'limit': self.limit}
                self.response(200, 'Images list.', output, stats=stats)

    @asynchronous
    @engine
    @api_authenticated
    def post(self, updopt=None):
        info(updopt)
        # if updopt == 'start':
        #     info('Success calling from itself.')
        #     self.response(200, 'Success calling from itself.')
        #     return
        # create a new image
        ########################################################################
        # Checking everything
        ########################################################################
        if not updopt:
            self.response(400, 'Uploads must be requested \
                calling /images/upload.')
            return
        # if not self.s3con:
        #    self.response(500, 'Fail to connect to S3. You must request support.')
        #    return
        # Check if file was sent and if its hash md5 already exists
        if 'image' not in self.input_data.keys():
            self.response(400, 'The request to add image require the key \
                "image" with the file encoded with base64.')
            return
        if 'joined' in self.input_data.keys():
            self.response(400, 'The "joined" attribute can\'t be defined for a new image.')
            return
        # Check if its a valid image
        dirfs = dirname(realpath(__file__))
        imgname = dirfs + '/' + str(uuid4()) + '.img'
        try:
            fh = open(imgname, 'wb')
            fh.write(b64decode(self.input_data['image']))
            fh.close()
        except Exception as e:
            self.remove_file(imgname)
            self.response(400, 'The encoded image is invalid, \
                you must remake the encode using base64.')
            return
        # Ok, image is valid
        # Now, check if it already exists in the database
        image_file = open(imgname, 'rb').read()
        filehash = md5(image_file).hexdigest()
        imgaexists = yield self.Images.find_one(
            {'hashcheck': filehash})
        if imgaexists:
            self.remove_file(imgname)
            info('File already exists!')
            self.response(409, 'The file already exists in the system.')
            return
        #####
        # everything checked, so good to go.
        #####
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(Image)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid, Image.collection())
        # prepare new obj
        dt = datetime.now()
        newobj['created_at'] = dt
        newobj['updated_at'] = dt
        fields_needed = ['image_set_id', 'is_public', 'image_tags']
        for field in fields_needed:
            if field not in self.input_data.keys():
                self.remove_file(imgname)
                self.response(400, 'You must submit the field {}.'.format(field))
                return
            else:
                newobj[field] = self.input_data[field]
        imgsetid = self.input_data['image_set_id']
        isexists = yield self.ImageSets.find_one({'iid': imgsetid})
        if isexists:
            newobj['image_set_iid'] = imgsetid
            del newobj['image_set_id']
        else:
            self.remove_file(imgname)
            self.response(400, "Image set id referenced doesn't exist.")
            return
        try:
            folder_name = 'imageset_' + str(isexists['iid']) + '_' + str(isexists['_id'])
            url = folder_name + '/' + dt.date().isoformat() + '_image_' + str(newobj['iid']) + '_'
            newobj['url'] = url
            # adding the hash pre calculed
            newobj['hashcheck'] = filehash
            # info(newobj)
            if 'exif_data' in newobj.keys() and isinstance(newobj['exif_data'], dict):
                newobj['exif_data'] = dumps(newobj['exif_data'])
            else:
                info('No exif data found.')
                newobj['exif_data'] = {}
            # Force joined as None since only associated imagesets can have images joined to the primary imageset
            newobj['joined'] = 0
            # info(newobj)
            newimage = Image(newobj)
            newimage.validate()
            # the new object is valid, so try to save
            try:
                newsaved = yield self.Images.insert(newimage.to_native())
                updurl = yield self.Images.update({'_id': newsaved}, {'$set': {'url': url + str(newsaved)}})
                info(updurl)
                output = newimage.to_native()
                # File data saved, now start to
                output['obj_id'] = str(newsaved)
                output['url'] = url + str(newsaved)
                output['image_set_id'] = output['image_set_iid']
                del output['image_set_iid']
                self.switch_iid(output)
                # if is Cover
                if self.input_data['iscover']:
                    updiscover = self.ImageSets.update(
                        {'iid': output['image_set_id']},
                        {'$set': {'updated_at': datetime.now(), 'main_image_iid': output['id']}})
                    info(updiscover)
                # Info to processing image
                self.process = True
                self.imgname = imgname
                self.imgid = str(output['id'])
                self.dt = dt
                self.imgobjid = output['obj_id']
                self.folder_name = folder_name
                # Remove Imageset Cache
                rem = yield Task(self.cache_remove, output['image_set_id'], 'imgset')
                # Returning success
                self.response(201, 'New image saved. The image processing will start for this new image.', output)
            except ValidationError as e:
                self.remove_file(imgname)
                self.response(400, 'Fail to save image. Errors: ' + str(e) + '.')
        except ValidationError as e:
            self.remove_file(imgname)
            # received data is invalid in some way
            self.response(400, 'Invalid input data. Errors: ' + str(e) + '.')

    @asynchronous
    @coroutine
    @api_authenticated
    def put(self, image_id=None):
        # update an image
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(Image)
        fields_allowed_to_be_update = ['image_set_id', 'is_public', 'image_tags', 'joined']
        if 'joined' in self.input_data.keys():
            if len(self.input_data.keys()) > 1:
                self.response(400, 'When the "joined" is submitted, no other key should be sent together.')
                return
            else:
                imgobj = yield self.Images.find_one(
                    {'iid': int(image_id)})
                if imgobj:
                    imgset = yield self.ImageSets.find_one(
                        {'$and': [{'iid': int(imgobj['image_set_iid'])},
                                  {'animal_iid': {'$ne': None}}]})
                    # Check if is Primary and its associated
                    if imgset:
                        imgprim = yield self.Animals.find({}, {'primary_image_set_iid': 1, 'iid': 1}).to_list(None)
                        if imgset['iid'] in [x['primary_image_set_iid'] for x in imgprim]:
                            self.response(400, 'The image is already from a primary image set.')
                            return
                        id_imgset = None
                        for anim in imgprim:
                            if anim['iid'] == imgset['animal_iid']:
                                id_imgset = anim['primary_image_set_iid']
                                break
                        info('joined value = ' + str(self.input_data['joined']))
                        info('joined type = ' + str(type(self.input_data['joined'])))
                        vjoined = 0
                        try:
                            if self.input_data['joined']:
                                vjoined = int(id_imgset)
                        except Exception as e:
                            vjoined = 0
                        try:
                            jimgset = yield self.ImageSets.find_one(
                                {'iid': int(id_imgset)})
                            if jimgset:
                                resp = yield self.Images.update(
                                    {'iid': int(imgobj['iid'])},
                                    {'$set': {'joined': vjoined}})
                                info(resp)
                        except Exception as e:
                            self.response(400, 'Fail to join image to primary \
                                image set.')
                            return
                        self.response(200, 'Image joined with success.')
                        return
                    else:
                        self.response(400, 'Image set of image Id submitted not found.')
                        return
                else:
                    self.response(404, 'Image ID not found.')
                    return
        if 'image_set_id' in self.input_data.keys():
            imgiid = self.input_data['image_set_id']
            imgset = yield self.ImageSets.find_one({'iid': imgiid})
            if imgset:
                update_data['image_set_id'] = imgiid
            else:
                self.response(409, "Image set referenced doesn't exist.")
                return
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if image_id and update_ok:
            query = self.query_id(image_id)
            updobj = yield self.Images.find_one(query)
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
                        folder_name = 'imageset_' + str(imgset['iid']) + '_' + str(imgset['_id'])
                        url = folder_name + '/' + updobj['created_at'].date().isoformat() + '_image_' + str(updobj['iid']) + '_' + str(updobj['_id'])


                        # copy image
                        # No need to specify the target bucket if we're copying inside the same bucket
                        oldimgset = yield self.ImageSets.find_one({'iid': orig_imgset_id})
                        srcurl = self.settings['S3_FOLDER'] + '/imageset_' + str(oldimgset['iid']) + '_' + str(oldimgset['_id']) + '/'
                        srcurl = srcurl + updobj['created_at'].date().isoformat() + '_image_' + str(updobj['iid']) + '_' + str(updobj['_id'])


                        desurl = self.settings['S3_FOLDER'] + '/' + url
                    objupdid = ObjId(str(updobj['_id']))
                    del updobj['_id']
                    updobj = Image(updobj)
                    updobj.validate()
                    updobj = updobj.to_native()
                    # the object is valid, so try to save
                    try:
                        updobj['_id'] = objupdid
                        saved = yield self.Images.update(query, updobj)
                        info(saved)
                        # Ok, data saved so operate s3
                        # Copy the image to the new imageset
                        # Copy the full for backup
                        output = updobj
                        output['obj_id'] = str(objupdid)
                        del output['_id']
                        # Change iid to id in the output
                        self.switch_iid(output)

                        if 'image_set_id' in self.input_data.keys() and updobj['image_set_iid'] != imgiid:
                            # image set was changed
                            try:
                                bkpcopy = self.settings['S3_FOLDER'] + '/backup/' + updobj['created_at'].date().isoformat() + '_image_' + str(updobj['iid']) + '_' + str(updobj['_id'])


                            except Exception as e:
                                pass
                            # self.s3con.copy(srcurl+'_full.jpg', self.settings['S3_BUCKET'],bkpcopy+'_full.jpg')
                            if not s3_copy(self.settings['S3_ACCESS_KEY'], self.settings['S3_SECRET_KEY'], self.settings['S3_BUCKET'], srcurl + '_full.jpg', bkpcopy + '_full.jpg'):
                                info('Fail to copy ' + str(srcurl) + ' to ' + str(bkpcopy + '_full.jpg'))
                            for suf in ['_full.jpg', '_icon.jpg', '_medium.jpg', '_thumbnail.jpg']:
                                # Copy the files
                                # self.s3con.copy(srcurl+suf, self.settings['S3_BUCKET'],desurl+suf)
                                if not s3_copy(self.settings['S3_ACCESS_KEY'], self.settings['S3_SECRET_KEY'], self.settings['S3_BUCKET'], srcurl + suf, desurl + suf):
                                        info('Fail to copy ' + str(srcurl + suf) + ' to ' + str(desurl + suf))
                                # Delete the source file
                                # self.s3con.delete(srcurl+suf, self.settings['S3_BUCKET'])
                                if not s3_delete(self.settings['S3_ACCESS_KEY'], self.settings['S3_SECRET_KEY'], self.settings['S3_BUCKET'], srcurl + suf):
                                    info('Fail to delete ' + str(srcurl + suf))
                        output['image_set_id'] = output['image_set_iid']
                        del output['image_set_iid']

                        # self.finish(self.json_encode({'status': 'success', 'message': 'image updated', 'data':output}))
                        self.response(200, 'Image id ' + str(output['id']) + ' updated successfully.', output)
                    except Exception as e:
                        # duplicated index error
                        self.response(409, 'Key violation. Errors: ' + str(e) + '.')
                except ValidationError as e:
                    # received data is invalid in some way
                    self.response(400, 'Invalid input data. Errors: ' + str(e) + '.')
            else:
                self.response(404, 'Image not found.')
        else:
            self.response(400, 'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, image_id=None):
        # delete an image
        if image_id:
            query = self.query_id(image_id)
            updobj = yield self.Images.find_one(query)
            if updobj:
                # check for references
                try:
                    # info(updobj)
                    delobj = yield self.Images.remove(query)
                    info(delobj)
                    # Delete the source file
                    bkpcopy = self.settings['S3_FOLDER'] + '/backup/' + updobj['created_at'].date().isoformat() + '_image_' + str(updobj['iid']) + '_' + str(updobj['_id']) + '_full.jpg'
                    info(bkpcopy)
                    imgset = yield self.ImageSets.find_one({'iid': updobj['image_set_iid']})
                    srcurl = self.settings['S3_FOLDER'] + '/imageset_' + str(imgset['iid']) + '_' + str(imgset['_id']) + '/'
                    srcurl = srcurl + updobj['created_at'].date().isoformat() + '_image_' + str(updobj['iid']) + '_' + str(updobj['_id'])


                    # try:
                    #    self.s3con.delete(bkpcopy, self.settings['S3_BUCKET'])
                    # except Exception as e:
                    #    pass
                    # Remove joined info from imagesets
                    resp = yield self.ImageSets.update({'main_image_iid': updobj['iid']}, {'$set': {'main_image_iid': None}})
                    info(resp)
                    rmlist = list()
                    try:
                        for suf in ['_full.jpg', '_icon.jpg', '_medium.jpg', '_thumbnail.jpg']:
                            # self.s3con.delete(srcurl+suf, self.settings['S3_BUCKET'])
                            rmlist.append(srcurl + suf)
                    except Exception as e:
                        self.response(200, 'Image successfully deleted but can\'t remove files from S3. Errors: %s.' % (str(e)))
                        return
                    if len(rmlist):
                        rmladd = yield self.db.dellist.insert({'list': rmlist, 'ts': datetime.now()})
                        info(rmladd)
                    self.response(200, 'Image successfully deleted.')
                except Exception as e:
                    self.response(500, 'Fail to delete image. Errors: %s.' % (str(e)))
            else:
                self.response(404, 'Image not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')

    def list(self, objs, callback=None):
        """Implement the list output used for UI in the website."""
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            url = self.imgurl(x['url'], 'icon')
            obj['url'] = url
            output.append(obj)
        return output


class ImagesVocHandler(BaseHandler, ProcessMixin):
    """A class that handles requests about VOC files."""
    SUPPORTED_METHODS = ('POST')

    @asynchronous
    @engine
    @api_authenticated
    def post(self, process=False):
        info(process)
        dirfs = dirname(realpath(__file__))
        # upload_folder = dirfs + '/upload_folder'
        # info(upload_folder)
        # if not exists(upload_folder):
        #     os.mkdir(upload_folder)
        if process == 'start':
            dictheaders = {}
            # if hasattr(self, 'current_user') and self.current_user and 'token' in self.current_user:
            #     dictheaders['Linc-Api-AuthToken'] = self.current_user.get('token', '')
            #     info(dictheaders)
            info(self.input_data)
            info("Launching ThreadPoolExecutor")
            EXECUTOR = ThreadPoolExecutor(max_workers=2)
            future = EXECUTOR.submit(process_voc, self, dirfs, self.input_data["API_URL"], self.input_data)
            # yield future
            # future.add_done_callback(lambda future: info("Processing has been done.))
            # future.add_done_callback(lambda future: send_to_api(future.result()))
            self.response(200, 'Received start.')
            return
        # Check whether image file.
        elif 'image_file' in self.input_data.keys():
            image_file = self.input_data['image_file']
            imgname = dirfs + '/' + image_file['filename']
            try:
                # Save image
                fh = open(imgname, 'wb')
                fh.write(b64decode(image_file['image']))
                fh.close()
                del image_file['image']
                # Save image metadata
                fh = open(splitext(imgname)[0] + '.json', 'w')
                fh.write(dumps(image_file))
                fh.close()
            except Exception as e:
                self.remove_file(imgname)
                self.response(400, 'The encoded image is invalid, \
                    you must remake the encode using base64.')
                return
            self.response(200, "Image file received.")
            return
        # Check whether voc file.
        elif 'xml_file' in self.input_data.keys():
            xmlname = dirfs + '/' + self.input_data['xml_file']['filename']
            try:
                fh = open(xmlname, 'wb')
                fh.write(b64decode(self.input_data['xml_file']['content']))
                fh.close()
                self.response(200, "Voc file received.")
                return
            except Exception as e:
                self.remove_file(xmlname)
                self.response(400, 'The encoded voc file is invalid, \
                    you must remake the encode using base64.')
                return
        else:
            self.response(400, 'Neither image or xml file received.')
            return

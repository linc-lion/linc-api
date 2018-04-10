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
# For more information or to contact visit linclion.org or
# email tech@linclion.org

from tornado.web import asynchronous
from tornado.gen import coroutine, Task, engine
from handlers.base import BaseHandler
from models.organization import Organization
from models.animal import Animal
from models.imageset import ImageSet, Image
from models.cv import CVRequest, CVResult
from bson import ObjectId as ObjId
from datetime import datetime
from json import dumps, loads
from tornado.escape import json_decode
from schematics.exceptions import ValidationError
from lib.rolecheck import allowedRole, refusedRole, api_authenticated
from logging import info


class ImageSetsHandler(BaseHandler):
    """A class that handles requests about image sets informartion
    """

    def query_id(self, imageset_id):
        """This method configures the query that will find an object"""
        try:
            query = {'iid': int(imageset_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(imageset_id)}
            except Exception as e:
                self.response(400, 'Invalid id key.')
                return
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, imageset_id=None, param=None):
        if param == 'cvrequest':
            self.response(400, 'To request cv identification you must use POST method.')
            return
        if imageset_id == 'list':
            # Show a list for the website
            # Get imagesets from the DB
            output = yield Task(self.list)
            self.response(200, 'Imagesets list.', output)
        elif imageset_id and param == 'profile':
            query = self.query_id(imageset_id)
            imgset = yield self.settings['db'].imagesets.find_one(query)
            if imgset:
                imgprim = yield self.settings['db'][self.animals].find({}, {'primary_image_set_iid': 1}).to_list(None)
                imgprim = [x['primary_image_set_iid'] for x in imgprim]
                output = imgset
                if 'geopos_private' in output.keys():
                    output['geopos_private'] = imgset['geopos_private']
                else:
                    output['geopos_private'] = False
                output['obj_id'] = str(imgset['_id'])
                del output['_id']
                self.switch_iid(output)
                # Get organization name
                org = yield self.settings['db'].organizations.find_one({'iid': output['owner_organization_iid']})
                if org:
                    output['organization'] = org['name']
                    output['organization_id'] = org['iid']
                else:
                    output['organization'] = '-'
                    output['organization_id'] = '-'
                # Check animal
                if output['id'] in imgprim:
                    # it's a primary image set
                    output['is_primary'] = True
                    queryani = {'primary_image_set_iid': output['id']}
                else:
                    output['is_primary'] = False
                    queryani = {'iid': output['animal_iid']}
                animalobj = yield self.settings['db'][self.animals].find_one(queryani)
                if animalobj:
                    output['name'] = animalobj['name']
                    if 'dead' in animalobj.keys():
                        output['dead'] = animalobj['dead']
                    else:
                        output['dead'] = False
                else:
                    output['name'] = '-'
                    output['dead'] = None
                if 'date_of_birth' in output.keys() and output['date_of_birth']:
                    output['age'] = str(self.age(output['date_of_birth']))
                else:
                    output['age'] = '-'

                # output['organization_id'] = output['organization_iid']
                # del output['organization_iid']
                output['uploading_organization_id'] = output['uploading_user_iid']
                del output['uploading_user_iid']
                output['uploading_organization_id'] = output['uploading_organization_iid']
                del output['uploading_organization_iid']
                output['owner_organization_id'] = output['owner_organization_iid']
                del output['owner_organization_iid']
                output['main_image_id'] = output['main_image_iid']
                del output['main_image_iid']

                # Get image
                img = yield self.settings['db'].images.find_one({'iid': output['main_image_id']})
                if img:
                    output['image'] = self.settings['S3_URL'] + img['url'] + '_thumbnail.jpg'
                    output['thumbnail'] = self.settings['S3_URL'] + img['url'] + '_icon.jpg'
                else:
                    img = yield self.settings['db'].images.find(
                        {'image_set_iid': output['id']}).to_list(None)
                    if len(img) > 0:
                        output['image'] = self.settings['S3_URL'] + img[0]['url'] + '_thumbnail.jpg'
                        output['thumbnail'] = self.settings['S3_URL'] + img[0]['url'] + '_icon.jpg'
                    else:
                        output['image'] = ''
                        output['thumbnail'] = ''

                # obji = yield self.settings['db'].images.find_one({'iid':obj['main_image_iid']})
                # if obji:
                #     imgset_obj['thumbnail'] = self.settings['S3_URL']+obji['url']+'_icon.jpg'
                #     imgset_obj['image'] = self.settings['S3_URL']+obji['url']+'_medium.jpg'
                # else:
                #     obji = yield self.settings['db'].images.find({'image_set_iid':obj['iid']}).to_list(None)
                #     if len(obji) > 0:
                #         imgset_obj['thumbnail'] = self.settings['S3_URL']+obji[0]['url']+'_icon.jpg'
                #         imgset_obj['image'] = self.settings['S3_URL']+obji[0]['url']+'_medium.jpg'
                #     else:
                #         imgset_obj['thumbnail'] = ''
                #         imgset_obj['image'] = ''

                if output['location']:
                    output['latitude'] = output['location'][0][0]
                    output['longitude'] = output['location'][0][1]
                else:
                    output['latitude'] = None
                    output['longitude'] = None
                del output['location']
                if 'tag_location' not in output.keys():
                    output['tag_location'] = None

                # Getting cvrequest for this imageset
                info(output['id'])
                cvreq = yield self.settings['db'].cvrequests.find_one({'image_set_iid': output['id']})
                info(cvreq)
                if cvreq:
                    output['cvrequest'] = str(cvreq['_id'])
                    output['req_status'] = cvreq['status']
                    cvres = yield self.settings['db'].cvresults.find_one({'cvrequest_iid': cvreq['iid']})
                    if cvres:
                        output['cvresults'] = str(cvres['_id'])
                    else:
                        output['cvresults'] = None
                else:
                    output['req_status'] = None
                    output['cvrequest'] = None
                    output['cvresults'] = None
                output[self.animals + '_org_id'] = ''
                if output['animal_iid']:
                    animal_org_iid = yield self.settings['db'][self.animals].find_one({'iid': output['animal_iid']})
                    if animal_org_iid:
                        output[self.animals +
                               '_org_id'] = animal_org_iid['organization_iid']
                output[self.animal + '_id'] = output['animal_iid']
                del output['animal_iid']

                self.response(200, 'Imageset found.', output)
                return
            else:
                self.response(404, 'Imageset not found.')
                return
        elif imageset_id and param == 'gallery':
            query = self.query_id(imageset_id)
            objimgset = yield self.settings['db'].imagesets.find_one(query)
            if objimgset:
                # images = yield self.settings['db'].images.find(
                #    {'image_set_iid': objimgset['iid']}).to_list(None)
                images = yield \
                    self.settings['db'].images.find(
                        {'$or': [
                            {'image_set_iid': int(objimgset['iid'])},
                            {'joined': int(objimgset['iid'])}
                        ]}).to_list(None)
                output = dict()
                output['id'] = imageset_id
                cover = objimgset['main_image_iid']
                output['images'] = list()
                for img in images:
                    if 'joined' not in img.keys():
                        vjoined = False
                    else:
                        vjoined = (img['joined'] != None)
                    imgout = {'id': img['iid'], 'type': img[
                        'image_type'], 'is_public': img['is_public'],
                        'joined': vjoined}
                    if vjoined:
                        imgout['joined_from'] = img['image_set_iid']
                    if 'filename' in img.keys() and img['filename'] != '':
                        imgout['filename'] = img['filename']
                    else:
                        imgout['filename'] = 'undefined'
                    imgout['imgset_date_stamp'] = objimgset['date_stamp']
                    imgout['imgset_updated_at'] = objimgset['updated_at'].date().isoformat()
                    imgout['img_updated_at'] = img['updated_at'].date().isoformat()
                    imgout['img_date_stamp'] = None
                    if 'exif_data' in img.keys():
                        exifd = loads(img['exif_data'])
                        info(exifd)
                        if 'date_stamp' in exifd.keys() and exifd['date_stamp']:
                            imgout['img_date_stamp'] = datetime.strptime(
                                exifd['date_stamp'], '%Y-%m-%dT%H:%M:%S').date().isoformat()
                    for suf in ['_icon.jpg', '_medium.jpg', '_thumbnail.jpg']:
                        imgout[suf[1:-4]] = self.settings['S3_URL'] + img['url'] + suf
                    imgout['cover'] = (img['iid'] == cover)
                    output['images'].append(imgout)
                self.response(200, 'Gallery images for the image set ' +
                              str(imageset_id) + '.', output)
            else:
                self.response(404, 'Imageset not found.')
            return
        else:
            if imageset_id:
                query = self.query_id(imageset_id)
                objimgsets = yield self.settings['db'].imagesets.find(query).to_list(None)
            else:
                objimgsets = yield self.settings['db'].imagesets.find().to_list(None)
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
                    if 'tag_location' in objimgset.keys():
                        output['tag_location'] = objimgset['tag_location']
                    else:
                        output['tag_location'] = None
                    if 'geopos_private' in objimgset.keys():
                        output['geopos_private'] = objimgset['geopos_private']
                    else:
                        output['geopos_private'] = False
                    if 'joined' in objimgset.keys():
                        output['joined'] = objimgset['joined']
                    else:
                        output['joined'] = []
                    output['obj_id'] = str(objimgset['_id'])
                    del output['_id']
                    output[self.animal + '_id'] = objimgset['animal_iid']
                    del output['animal_iid']
                    output['main_image_id'] = objimgset['main_image_iid']
                    del output['main_image_iid']
                    loutput.append(output)
                self.set_status(200)
                if imageset_id:
                    loutput = loutput[0]
                self.response(200, 'Image set required.',loutput)
            else:
                self.response(404, 'Imageset id not found.')

    @asynchronous
    @coroutine
    @api_authenticated
    def post(self, imageset_id=None, cvrequest=None):
        if not imageset_id:
            # create a new imageset or new cvrequest
            # parse data recept by POST and get only fields of the object
            newobj = self.parseInput(ImageSet)
            # getting new integer id
            newobj['iid'] = yield Task(self.new_iid, ImageSet.collection())
            dt = datetime.now()
            newobj['created_at'] = dt
            newobj['updated_at'] = dt
            # validate the input
            fields_needed = ['uploading_user_id', 'uploading_organization_id', 'owner_organization_id',
                             'is_verified', 'gender', 'date_of_birth',
                             'tags', 'date_stamp', 'notes', self.animal + '_id', 'main_image_id', 'geopos_private']
            keys = list(self.input_data.keys())
            for field in fields_needed:
                if field not in keys:
                    self.response(400, 'You must provide the key for ' +
                                  field + ' even it has the value = null.')
                    return
            # check if date_stamp are valid
            if newobj['date_stamp']:
                try:
                    dts = datetime.strptime(newobj['date_stamp'], "%Y-%m-%d").date()
                    newobj['date_stamp'] = str(dts)
                except Exception as e:
                    self.response(
                        400, 'Invalid date_stamp. you must provide it in format YYYY-MM-DD.')
                    return
            if newobj['date_of_birth']:
                try:
                    newobj['date_of_birth'] = datetime.strptime(newobj['date_of_birth'], "%Y-%m-%d")
                except Exception as e:
                    self.response(
                        400, 'Invalid date_of_birth. you must provide it in format YYYY-MM-DD.')
                    return
            # check if user exists
            useriid = self.input_data['uploading_user_id']
            userexists = yield self.settings['db'].users.find_one({'iid': useriid})
            if userexists:
                newobj['uploading_user_iid'] = useriid
            else:
                self.response(409, "Uploading user id referenced doesn't exist.")
                return
            # check if organizations exists
            orgiid = self.input_data['uploading_organization_id']
            orgexists = yield self.settings['db'].organizations.find_one({'iid': orgiid})
            if orgexists:
                newobj['uploading_organization_iid'] = orgiid
            else:
                self.response(409, "Uploading organization id referenced doesn't exist.")
                return
            oorgiid = self.input_data['owner_organization_id']
            oorgexists = yield self.settings['db'].organizations.find_one({'iid': oorgiid})
            if oorgexists['iid'] == orgiid:
                newobj['owner_organization_iid'] = oorgiid
            else:
                self.response(409, "Owner organization id referenced doesn't exist.")
                return
            if 'latitude' in self.input_data.keys() and self.input_data['latitude'] and \
                    'longitude' in self.input_data.keys() and self.input_data['longitude']:
                newobj['location'] = [[self.input_data['latitude'], self.input_data['longitude']]]
            newobj['animal_iid'] = self.input_data[self.animal + '_id']
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
                output[self.animal + '_id'] = output['animal_iid']
                del output['animal_iid']

                self.set_status(200)
                self.finish(self.json_encode(
                    {'status': 'success', 'message': 'new image set added', 'data': output}))
            except ValidationError as e:
                self.response(400, "Invalid input data. Error: " + str(e) + '.')
                return
        else:
            query = self.query_id(imageset_id)
            imgchk = yield self.settings['db'].imagesets.find_one(query)
            if imgchk:
                cvreqchk = yield self.settings['db'].cvrequests.find_one({'image_set_iid': imgchk['iid']})
                if cvreqchk:
                    self.response(
                        400, 'A request for indentification of this imageset already exists in the database.')
                    return
                if self.animals not in self.input_data.keys():
                    self.response(400, 'The cvrequest needs a list of ' + self.settings[
                                  'animals'] + ' id like: { "' + self.animals + '" : [<id>,...] }.')
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
                             self.animals: list()
                             }
                            }
                    query_images = {'image_set_iid': imgchk['iid']}
                    imgs = yield self.settings['db'].images.find(query_images).to_list(None)
                    limgs = list()
                    for img in imgs:
                        limgs.append({'id': img['iid'], 'type': img['image_type'], 'url': self.settings[
                                     'S3_URL'] + img['url'] + '_full.jpg'})
                    animals = self.input_data[self.animals]
                    animalscheck = yield self.settings['db'][self.animals].find({'iid': {'$in': animals}}).to_list(None)
                    if not animalscheck:
                        self.response(400, 'No id valid in the list of ' +
                                      self.animals + ' passed.')
                        return
                    lanimals = list()
                    for animal in animalscheck:
                        url = self.settings['url'] + self.animals + '/'
                        lanimals.append({'id': animal['iid'], 'url': url + str(animal['iid'])})
                    body['identification']['images'] = limgs
                    body['identification'][self.animals] = lanimals
                    sbody = dumps(body)
                    # info(sbody)
                    try:
                        response = yield Task(self.api,
                                              url=self.settings['CVSERVER_URL_IDENTIFICATION'],
                                              method='POST',
                                              body=sbody,
                                              auth_username=self.settings['CV_USERNAME'],
                                              auth_password=self.settings['CV_PASSWORD'])
                        rbody = json_decode(response.body)
                        # Create a cvrequest mongodb object for this ImageSet
                        newobj = dict()
                        newobj['iid'] = yield Task(self.new_iid, CVRequest.collection())
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
                        self.finish(self.json_encode(
                            {'status': 'success', 'message': response.reason, 'data': output}))
                    except ValidationError as e:
                        self.set_status(500)
                        self.finish(
                            {'status': 'error', 'message': 'Fail to execute the request for identification. Errors: ' + str(e)})
                else:
                    self.response(400, 'Bad request.')
            else:
                self.response(404, 'Imageset id not found.')

    @asynchronous
    @coroutine
    @api_authenticated
    def put(self, imageset_id=None):
        # update an imageset
        if imageset_id:
            # getting the object
            query = self.query_id(imageset_id)
            objimgset = yield self.settings['db'].imagesets.find_one(query)
            if objimgset:
                dt = datetime.now()
                objimgset['updated_at'] = dt
                # validate the input
                fields_allowed = ['uploading_user_id', 'uploading_organization_id', 'owner_organization_id',
                                  'is_verified', 'latitude', 'longitude', 'tag_location', 'gender', 'date_of_birth',
                                  'tags', 'date_stamp', 'notes', self.animal + '_id', 'main_image_id', 'geopos_private']
                update_data = dict()
                # Remove join reference when remove association
                animal_cfg = self.animal + '_id'
                if animal_cfg in self.input_data.keys():
                    if self.input_data[animal_cfg] == None:
                        # Remove joined referenced
                        assocanimalid = objimgset['animal_iid']
                        primimgsetid = yield self.settings['db'][self.animals].find_one({'iid':assocanimalid})
                        if primimgsetid:
                            primimgsetid = primimgsetid['primary_image_set_iid']
                            resp = yield self.settings['db'].images.update({'$and': [{'image_set_iid': objimgset['iid']},  {'joined':{'$ne':None}}]},{'$set':{'joined':None}},multi=True)
                            imgslist = yield self.settings['db'].images.find({'image_set_iid':objimgset['iid']}).to_list(None)
                            imgslist = [int(x['iid']) for x in imgslist]
                            resp = self.settings['db'].imagesets.update({'main_image_iid':{'$in':imgslist}},{'$set':{'main_image_iid':None}},multi=True)
                for k, v in self.input_data.items():
                    if k in fields_allowed:
                        update_data[k] = v
                for field in fields_allowed:
                    if field in update_data.keys():
                        if field in ['uploading_user_id', 'uploading_organization_id', 'owner_organization_id',
                                     self.animal + '_id', 'main_image_id']:
                            vkey = field.index('_id')
                            vkey = field[:vkey] + '_iid'
                            cmd = "objimgset['" + vkey + "'] = " + str(update_data[field])
                            exec(cmd)
                            if vkey == self.animal + '_iid':
                                objimgset['animal_iid'] = update_data[
                                    self.animal + '_id']
                                del objimgset[self.animal + '_iid']
                            del update_data[field]
                            continue
                        elif field in ['date_stamp', 'date_of_birth']:
                            # check if date_stamp are valid
                            if update_data[field]:
                                try:
                                    dts = datetime.strptime(update_data[field], "%Y-%m-%d")
                                    info(dts)
                                    if field == 'date_stamp':
                                        objimgset['date_stamp'] = str(dts.date())
                                        continue
                                    else:
                                        objimgset['date_of_birth'] = dts
                                        continue
                                except Exception as e:
                                    self.response(400, 'Invalid ' + field + '.')
                                    return
                        elif field in ['latitude', 'longitude']:
                            if 'latitude' in update_data.keys() and update_data['latitude'] and \
                               'longitude' in update_data.keys() and update_data['longitude']:
                                info(update_data[field])
                                objimgset['location'] = [[0, 0]]
                                objimgset['location'][0][0] = float(update_data['latitude'])
                                objimgset['location'][0][1] = float(update_data['longitude'])
                                del update_data['latitude']
                                del update_data['longitude']
                            else:
                                objimgset['location'] = None
                            continue
                        # elif field == 'is_verified':
                        #    objimgset['is_verified'] = \
                        #    update_data['is_verified']
                        #    continue
                        objimgset[field] = update_data[field]

                # check if user exists
                useriid = objimgset['uploading_user_iid']
                userexists = yield \
                    self.settings['db'].users.find_one({'iid': useriid})
                if not userexists:
                    self.response(409, "Uploading user id \
                        referenced doesn't exist.")
                    return
                # check if organizations exists
                orgiid = objimgset['uploading_organization_iid']
                orgexists = yield \
                    self.settings['db'].organizations.find_one({'iid': orgiid})
                if not orgexists:
                    self.response(409, "Uploading organization id \
                        referenced doesn't exist.")
                    return
                oorgiid = objimgset['owner_organization_iid']
                oorgexists = yield \
                    self.settings['db'].organizations.find_one(
                        {'iid': oorgiid})
                if oorgexists['iid'] != oorgiid:
                    self.response(409, "Owner organization id \
                        referenced doesn't exist.")
                    return
                if objimgset['animal_iid']:
                    aniexists = yield \
                        self.settings['db'][self.animals].find_one(
                            {'iid': objimgset['animal_iid']})
                    if aniexists['iid'] != objimgset['animal_iid']:
                        self.response(409, 'The ' + self.animal +
                                      " id sent doesn't exist.")
                        return
                # Check for Verification request
                if animal_cfg in self.input_data.keys() and self.input_data[animal_cfg] != None:
                    aniexists = yield \
                        self.settings['db'][self.animals].find_one(
                            {'iid': self.input_data[animal_cfg]})
                    animal_org_iid = aniexists['organization_iid']
                    imageset_org_iid = objimgset['owner_organization_iid']
                    if animal_org_iid != imageset_org_iid:
                        # Request Verification
                        # Get emails from the
                        userslist = yield self.settings['db'].users.find({'organization_iid':animal_org_iid}).to_list(None)
                        emails = [user['email'] for user in userslist]
                        orgname = yield self.settings['db'].organizations.find_one({'iid':int(imageset_org_iid)})
                        aniorg = yield self.settings['db'].organizations.find_one({'iid':int(aniexists['organization_iid'])})
                        if not orgname:
                            orgname = 'no name defined'
                        else:
                            orgname = orgname['name']
                        if len(emails) > 0:
                            for eaddr in emails:
                                msg = """From: %s\nTo: %s\nSubject: LINC Lion: Request for verification\n\nThis email was created by the system due to an association request of an image set with a lion from another organization.\nThe image set was associated with the lion:\n\nId: %s\nName: %s\nOrganization: %s\n\nThe image set is presented below:\n\nId: %s\nOrganization: %s\nLink: %s (accessible for previous logged users)\n\nPlease, go to the LINC website to verify (accept) or remove the request for association.\n\nLinc Lion Team\nhttps://linc.linclion.org/\n

                                """
                                msg = msg % (self.settings['EMAIL_FROM'],eaddr,aniexists['iid'],aniexists['name'],aniorg['name'],imageset_id,orgname, 'https://linc.linclion.org/#/imageset/' + str(imageset_id))
                                pemail = yield Task(self.sendEmail,eaddr,msg)
                if 'is_verified' in self.input_data.keys() and self.input_data['is_verified'] == True:
                    imgset2ver = yield self.settings['db'].imagesets.find_one(query)
                    userslist = yield self.settings['db'].users.find({'organization_iid':imgset2ver['owner_organization_iid']}).to_list(None)
                    animobj = yield self.settings['db'][self.animals].find_one({'iid':imgset2ver['animal_iid']})
                    if animobj:
                        aniorg = yield self.settings['db'].organizations.find_one({'iid':animobj['organization_iid']})
                        imgorg = yield self.settings['db'].organizations.find_one({'iid':imgset2ver['owner_organization_iid']})
                        emails = [user['email'] for user in userslist]
                        if len(emails) > 0:
                            for eaddr in emails:
                                msg = """From: %s\nTo: %s\nSubject: LINC Lion: Image set %s was verified\n\nThis email was created by the system as a notification for the accept of an image set association with a lion from another organization.\nThe image set:\n\nId: %s\nOrganization: %s\nLink: %s (accessible for previous logged users)\n\nIt was associated with the lion:\n\nId: %s\nName: %s\nOrganization: %s\n
                                \nLinc Lion Team\nhttps://linc.linclion.org/\n

                                """
                                msg = msg % (self.settings['EMAIL_FROM'],eaddr,imageset_id,imageset_id,imgorg['name'], 'https://linc.linclion.org/#/imageset/' + str(imageset_id),animobj['iid'],animobj['name'],aniorg['name'],)
                                pemail = yield Task(self.sendEmail,eaddr,msg)
                try:
                    imgid = ObjId(objimgset['_id'])
                    del objimgset['_id']
                    info(objimgset)
                    objimgset = ImageSet(objimgset)
                    objimgset.validate()
                    objimgset = objimgset.to_native()
                    # objimgset['_id'] = imgid
                    updnobj = yield \
                        self.settings['db'].imagesets.update(
                            {'_id': imgid}, {'$set': objimgset}, upsert=True)
                    info(updnobj)
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
                    output[self.animal + '_id'] = output['animal_iid']
                    del output['animal_iid']
                    self.set_status(200)
                    self.finish(self.json_encode(
                        {'status': 'success', 'message': 'image set updated', 'data': output}))
                except ValidationError as e:
                    self.response(400, "Invalid input data. Error: " + str(e) + '.')
                    return
            else:
                self.response(404, 'Imageset id not found.')
        else:
            self.response(
                400, 'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, imageset_id=None):
        # delete an imageset
        if imageset_id:
            query = self.query_id(imageset_id)
            imgobj = yield self.settings['db'].imagesets.find_one(query)
            if imgobj:
                # check if it's a primary image set
                imgprim = yield self.settings['db'][self.animals].find({}, {'primary_image_set_iid': 1}).to_list(None)
                imgprim = [int(x['primary_image_set_iid']) for x in imgprim]
                if int(imageset_id) in imgprim:
                    self.response(400, 'The image set ' + str(imageset_id) +
                                  ' is a primary one, it must be deleted through its ' + self.animal + '.')
                    return
                # 1 - Remove imaget set
                rmved = yield self.settings['db'].imagesets.remove({'iid': imgobj['iid']})
                info(str(rmved))
                # 2 - Remove images of the image set
                imgl = yield self.settings['db'].images.find({'image_set_iid': imgobj['iid']}).to_list(None)
                rmlist = list()
                for img in imgl:
                    # Remove joined referenced
                    resp = yield self.settings['db'].imagesets.update({'main_image_iid':img['iid']},{'$set':{'main_image_iid':None}})
                    # Delete the source file
                    srcurl = self.settings['S3_FOLDER'] + '/imageset_' + \
                        str(imgobj['iid']) + '_' + str(imgobj['_id']) + '/'
                    srcurl = srcurl + img['created_at'].date().isoformat() + \
                        '_image_' + str(img['iid']) + '_' + str(img['_id'])
                    try:
                        for suf in ['_full.jpg', '_icon.jpg', '_medium.jpg', '_thumbnail.jpg']:
                            rmlist.append(srcurl + suf)
                    except Exception as e:
                        self.response(500, 'Fail to delete image in S3. Errors: ' + str(e) + '.')
                        return
                if len(rmlist) > 0:
                    rmladd = yield self.settings['db'].dellist.insert({'list': rmlist, 'ts': datetime.now()})
                    info(rmladd)
                rmved = yield self.settings['db'].images.remove({'image_set_iid': imgobj['iid']}, multi=True)
                info(str(rmved))
                # 3 - Removing cvrequests and cvresults
                cvreql = yield self.settings['db'].cvrequests.find({'image_set_iid': imgobj['iid']}).to_list(None)
                for cvreq in cvreql:
                    # Removing cvresult
                    rmved = yield self.settings['db'].cvresults.remove({'cvrequest_iid': cvreq['iid']})
                    info(str(rmved))
                    # Removing cvrequest
                    rmved = yield self.settings['db'].cvrequests.remove({'_id': cvreq['_id']})
                    info(str(rmved))
            else:
                self.response(404, 'Image set not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')

    @asynchronous
    @engine
    def list(self, callback=None):
        objs_imgsets = yield self.settings['db'].imagesets.find().to_list(None)
        animals = yield self.settings['db'][self.animals].find().to_list(None)
        primary_imgsets_list = list()
        animals_names = dict()
        dead_dict = dict()
        for x in animals:
            animals_names[x['iid']] = x['name']
            if x['primary_image_set_iid']:
                primary_imgsets_list.append(x['primary_image_set_iid'])
            if 'dead' in x.keys():
                dead_dict[x['iid']] = x['dead']
            else:
                dead_dict[x['iid']] = False
        output = list()
        for obj in objs_imgsets:
            imgset_obj = dict()
            imgset_obj['obj_id'] = str(obj['_id'])
            imgset_obj['id'] = obj['iid']
            imgset_obj[self.animals + '_org_id'] = ''
            if obj['animal_iid']:
                imgset_obj['name'] = animals_names[obj['animal_iid']]
                imgset_obj['dead'] = dead_dict[obj['animal_iid']]
                imgset_obj[self.animal + '_id'] = obj['animal_iid']
                animal_org_iid = yield self.settings['db'][self.animals].find_one({'iid': obj['animal_iid']})
                if animal_org_iid:
                    imgset_obj[self.animals +
                               '_org_id'] = animal_org_iid['organization_iid']
            else:
                imgset_obj['name'] = '-'
                imgset_obj['dead'] = None
                imgset_obj[self.animal + '_id'] = None

            obji = yield self.settings['db'].images.find_one({'iid': obj['main_image_iid']})
            if obji:
                imgset_obj['thumbnail'] = self.settings['S3_URL'] + obji['url'] + '_icon.jpg'
                imgset_obj['image'] = self.settings['S3_URL'] + obji['url'] + '_medium.jpg'
            else:
                obji = yield self.settings['db'].images.find({'image_set_iid': obj['iid']}).to_list(None)
                if len(obji) > 0:
                    imgset_obj['thumbnail'] = self.settings['S3_URL'] + obji[0]['url'] + '_icon.jpg'
                    imgset_obj['image'] = self.settings['S3_URL'] + obji[0]['url'] + '_medium.jpg'
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

            if 'geopos_private' in obj.keys():
                imgset_obj['geopos_private'] = obj['geopos_private']
            else:
                imgset_obj['geopos_private'] = False
            if 'joined' in obj.keys():
                imgset_obj['joined'] = obj['joined']
            else:
                imgset_obj['joined'] = []
            if obj['location']:
                imgset_obj['latitude'] = obj['location'][0][0]
                imgset_obj['longitude'] = obj['location'][0][1]
            else:
                imgset_obj['latitude'] = None
                imgset_obj['longitude'] = None

            if 'tag_location' in obj.keys():
                imgset_obj['tag_location'] = obj['tag_location']
            else:
                imgset_obj['tag_location'] = None

            if obj['owner_organization_iid']:
                objo = yield self.settings['db'].organizations.find_one({'iid': obj['owner_organization_iid']})
                if objo:
                    imgset_obj['organization'] = objo['name']
                    imgset_obj['organization_id'] = obj['owner_organization_iid']
                else:
                    imgset_obj['organization'] = '-'
                    imgset_obj['organization_id'] = '-'

            imgset_obj['gender'] = obj['gender']
            imgset_obj['is_verified'] = obj['is_verified']
            imgset_obj['is_primary'] = (obj['iid'] in primary_imgsets_list)

            objcvreq = yield self.settings['db'].cvrequests.find_one({'image_set_iid': obj['iid']})
            if objcvreq:
                imgset_obj['cvrequest'] = str(objcvreq['_id'])
                imgset_obj['req_status'] = objcvreq['status']
            else:
                imgset_obj['cvrequest'] = None
                imgset_obj['req_status'] = None

            imgset_obj['cvresults'] = None
            if objcvreq:
                objcvres = yield self.settings['db'].cvresults.find_one({'cvrequest_iid': objcvreq['iid']})
                if objcvres:
                    imgset_obj['cvresults'] = str(objcvres['_id'])
            output.append(imgset_obj)
        callback(output)

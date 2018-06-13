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
from models.imageset import ImageSet
from models.cv import CVRequest
from bson import ObjectId as ObjId
from datetime import datetime
from json import dumps, loads
from schematics.exceptions import ValidationError
from lib.rolecheck import api_authenticated
from logging import info


class ImageSetsHandler(BaseHandler):
    """A class that handles requests about image sets informartion."""
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')

    def query_id(self, imageset_id):
        """The method configures the query that will find an object."""
        try:
            query = {'iid': int(imageset_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(imageset_id)}
            except Exception as e:
                self.response(400, 'Invalid id key. Error: ' + str(e) + '.')
                return
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, imageset_id=None, param=None):
        if param == 'cvrequest':
            self.response(
                400, 'CV requests are accepted if they are sent by POST method.')
            return
        current_user = yield self.Users.find_one({'email': self.current_user['username']})
        if not current_user:
            self.response(401, 'Authentication required.')
            return
        is_admin = current_user['admin']
        current_organization = yield self.db.organizations.find_one({'iid': current_user['organization_iid']})
        if imageset_id == 'list':
            # Show a list for the website
            # Get imagesets from the DB
            output = yield Task(self.list)
            self.response(200, 'Imagesets list.', output)
        elif imageset_id and param == 'profile':
            query = self.query_id(imageset_id)
            imgset = yield self.ImageSets.find_one(query)
            if imgset:
                imgprim = yield self.Animals.find({}, {'primary_image_set_iid': 1}).to_list(None)
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
                org = yield self.db.organizations.find_one({'iid': output['owner_organization_iid']})
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
                animalobj = yield self.Animals.find_one(queryani)
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
                output['uploading_organization_id'] = output['uploading_user_iid']
                del output['uploading_user_iid']
                output['uploading_organization_id'] = output['uploading_organization_iid']
                del output['uploading_organization_iid']
                output['owner_organization_id'] = output['owner_organization_iid']
                del output['owner_organization_iid']
                output['main_image_id'] = output['main_image_iid']
                del output['main_image_iid']

                # Get image
                img = yield self.Images.find_one({'iid': output['main_image_id']})
                if img:
                    output['image'] = self.settings['S3_URL'] + img['url'] + '_thumbnail.jpg'
                    output['thumbnail'] = self.settings['S3_URL'] + img['url'] + '_icon.jpg'
                else:
                    img = yield self.Images.find(
                        {'image_set_iid': output['id']}).to_list(None)
                    if len(img) > 0:
                        output['image'] = self.settings['S3_URL'] + img[0]['url'] + '_thumbnail.jpg'
                        output['thumbnail'] = self.settings['S3_URL'] + img[0]['url'] + '_icon.jpg'
                    else:
                        output['image'] = ''
                        output['thumbnail'] = ''
                can_show = (True if (is_admin or current_organization['iid'] == org['iid']) else False) if output['geopos_private'] else True
                if can_show:
                    if output['location']:
                        output['latitude'] = output['location'][0][0]
                        output['longitude'] = output['location'][0][1]
                    else:
                        output['latitude'] = None
                        output['longitude'] = None
                    if 'tag_location' not in output.keys():
                        output['tag_location'] = None
                else:
                    output['latitude'] = None
                    output['longitude'] = None
                    output['tag_location'] = None
                del output['location']

                # Getting cvrequest for this imageset
                info(output['id'])
                cvreq = yield self.CVRequests.find_one({'image_set_iid': output['id']})
                info(cvreq)
                if cvreq:
                    output['cvrequest'] = str(cvreq['_id'])
                    output['req_status'] = cvreq['status']
                    cvres = yield self.CVResults.find_one({'cvrequest_iid': cvreq['iid']})
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
                    animal_org_iid = yield self.Animals.find_one({'iid': output['animal_iid']})
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
            objimgset = yield self.ImageSets.find_one(query)
            if objimgset:
                # Check if is Primary Imageset
                imgprim = yield self.Animals.find_one({'iid': objimgset['animal_iid']}, {'primary_image_set_iid': 1})
                is_primary = False
                if imgprim and imgprim['primary_image_set_iid'] == objimgset['animal_iid']:
                    is_primary = True
                images = yield \
                    self.Images.find(
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
                        vjoined = (img['joined'] is not None)
                    imgout = {'id': img['iid'], 'tags': img['image_tags'],
                              'is_public': img['is_public'], 'joined': vjoined}
                    if vjoined:
                        if is_primary:
                            imgout['joined_from'] = objimgset['iid']
                            imgout['joined_to'] = img['image_set_iid']
                        else:
                            imgout['joined_from'] = img['image_set_iid']
                            imgout['joined_to'] = imgprim['primary_image_set_iid']
                    if 'filename' in img.keys() and img['filename'] != '':
                        imgout['filename'] = img['filename']
                    else:
                        imgout['filename'] = 'undefined'
                    imgout['imgset_date_stamp'] = objimgset['date_stamp']
                    imgout['imgset_updated_at'] = objimgset['updated_at'].date().isoformat()
                    imgout['updated_at'] = img['updated_at'].date().isoformat()
                    imgout['created_at'] = img['created_at'].date().isoformat()
                    imgout['date_stamp'] = None
                    if 'exif_data' in img.keys():
                        exifd = loads(img['exif_data'])
                        info(exifd)
                        if 'date_stamp' in exifd.keys() and exifd['date_stamp']:
                            imgout['date_stamp'] = datetime.strptime(
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
                objimgsets = yield self.ImageSets.find(query).to_list(None)
            else:
                objimgsets = yield self.ImageSets.find().to_list(None)
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
                self.response(200, 'Image set required.', loutput)
            else:
                self.response(404, 'Imageset id not found.')

    @asynchronous
    @coroutine
    @api_authenticated
    def post(self, imageset_id=None, cvrequest=None):
        if not imageset_id:
            response = yield Task(self.create_imageset, self.input_data)
            if response and response['code'] != 200:
                self.response(response['code'], response['message'])
                return
            self.set_status(200)
            self.finish(self.json_encode({'status': 'success', 'message': response['message'], 'data': response['data']}))
        else:
            query = self.query_id(imageset_id)
            imgchk = yield self.ImageSets.find_one(query)
            if imgchk:
                cvreqchk = yield self.CVRequests.find_one({'image_set_iid': imgchk['iid']})
                if cvreqchk:
                    self.response(
                        400, 'A request for indentification of this imageset already exists in the database.')
                    return
                if self.animals not in self.input_data.keys():
                    self.response(400, 'The cvrequest needs a list of ' + self.settings[
                                  'animals'] + ' id like: { "' + self.animals + '": [<id>,...] }.')
                    return
                if cvrequest:
                    check_algo = {'cv': False, 'whisker': False}
                    for v in self.input_data.get('classifier', []):
                        check_algo[v] = True
                    if not any(check_algo.values()):
                        self.response(400, 'Request invalid, please select at least one algorithm.')
                        return
                    # Send a request for identification in the CV Server
                    # The new cv request support two algorithms
                    request_base_body = dict()
                    request_base_body['classifiers'] = check_algo
                    request_base_body['age'] = self.age(imgchk['date_of_birth']) if imgchk['date_of_birth'] else None
                    request_base_body['gender'] = imgchk['gender']
                    animalscheck = yield self.Animals.find({'iid': {'$in': self.input_data[self.animals]}}).to_list(None)
                    if not animalscheck:
                        self.response(400, 'No id valid in the list of ' +
                                      self.animals + ' passed.')
                        return
                    lanimals = [x['iid'] for x in animalscheck]
                    info('List passed: {}'.format(self.input_data[self.animals]))
                    info('List found : {}'.format(lanimals))
                    request_base_body[self.animals] = lanimals
                    request_base_body[self.animals + '_submitted'] = self.input_data[self.animals]
                    cv_imgs = yield self.Images.find(
                        {'image_tags': ['cv'],
                         'image_set_iid': imgchk['iid']}).to_list(None)
                    wh_imgs = yield self.Images.find(
                        {'$or': [{'image_tags': ['whisker']},
                                 {'image_tags': ['whisker-left']},
                                 {'image_tags': ['whisker-right']}],
                         'image_set_iid': imgchk['iid']}).to_list(None)
                    cv_calls = list()
                    info(check_algo)
                    if check_algo.get('cv', False):
                        for x in cv_imgs:
                            cv_calls.append({
                                'type': 'cv',
                                'url': self.settings['S3_URL'] + x['url'] + '_full.jpg'})
                    wh_calls = list()
                    if check_algo.get('whisker', False):
                        for x in wh_imgs:
                            wh_calls.append({
                                'type': 'whisker',
                                'url': self.settings['S3_URL'] + x['url'] + '_full.jpg'})
                    if cv_calls or wh_calls:
                        request_base_body['cv_calls'] = cv_calls if cv_calls else []
                        request_base_body['wh_calls'] = wh_calls if wh_calls else []
                        # Create a cvrequest mongodb object for this ImageSet
                        newobj = dict()
                        newobj['iid'] = yield Task(self.new_iid, CVRequest.collection())
                        # This will be get from the user that do the request
                        newobj['requesting_organization_iid'] = self.current_user['org_id']
                        newobj['image_set_iid'] = imageset_id
                        newobj['status'] = 'created'
                        newobj['request_body'] = dumps(request_base_body)
                        try:
                            newsaved = CVRequest(newobj)
                            newsaved.validate()
                            newreqadd = yield self.CVRequests.insert(newsaved.to_native())
                        except Exception as e:
                            info(e)
                            self.response(500, 'Fail to create the CV Request.')
                            return
                        # Remove cache from this imageset
                        rem = yield Task(self.cache_remove, str(imageset_id), 'imgset')
                        info(rem)
                        output = newsaved.to_native()
                        output['obj_id'] = str(newreqadd)
                        self.switch_iid(output)
                        del output['request_body']
                        output['requesting_organization_id'] = output['requesting_organization_iid']
                        del output['requesting_organization_iid']
                        output['image_set_id'] = output['image_set_iid']
                        del output['image_set_iid']
                        self.response(200, 'Image', output)
                    else:
                        self.response(400, 'The image set does not have images with the tags cv or whisker.')
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
            # Clear cache for the imageset_id
            rem = yield Task(self.cache_remove, str(imageset_id), 'imgset')
            info(rem)
            # getting the object
            query = self.query_id(imageset_id)
            objimgset = yield self.ImageSets.find_one(query)
            if objimgset:
                # objiid = objimgset['iid']
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
                    if self.input_data[animal_cfg] is None:
                        # Remove joined referenced
                        assocanimalid = objimgset['animal_iid']
                        primimgsetid = yield self.Animals.find_one({'iid': assocanimalid})
                        if primimgsetid:
                            primimgsetid = primimgsetid['primary_image_set_iid']
                            resp = yield self.Images.update(
                                {'$and': [{'image_set_iid': objimgset['iid']},
                                          {'joined': {'$ne': None}}]},
                                {'$set': {'joined': None}},
                                multi=True)
                            info(resp)
                            imgslist = yield self.Images.find({'image_set_iid': objimgset['iid']}).to_list(None)
                            imgslist = [int(x['iid']) for x in imgslist]
                            resp = self.ImageSets.update(
                                {'main_image_iid': {'$in': imgslist}}, {'$set': {'main_image_iid': None}},
                                multi=True)
                            info(resp)
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
                    self.Users.find_one({'iid': useriid})
                if not userexists:
                    self.response(409, "Uploading user id \
                        referenced doesn't exist.")
                    return
                # check if organizations exists
                orgiid = objimgset['uploading_organization_iid']
                orgexists = yield \
                    self.db.organizations.find_one({'iid': orgiid})
                if not orgexists:
                    self.response(409, "Uploading organization id \
                        referenced doesn't exist.")
                    return
                oorgiid = objimgset['owner_organization_iid']
                oorgexists = yield \
                    self.db.organizations.find_one(
                        {'iid': oorgiid})
                if oorgexists['iid'] != oorgiid:
                    self.response(409, "Owner organization id \
                        referenced doesn't exist.")
                    return
                if objimgset['animal_iid']:
                    aniexists = yield \
                        self.Animals.find_one(
                            {'iid': objimgset['animal_iid']})
                    if aniexists['iid'] != objimgset['animal_iid']:
                        self.response(409, 'The ' + self.animal +
                                      " id sent doesn't exist.")
                        return
                # Check for Verification request
                if animal_cfg in self.input_data.keys() and self.input_data[animal_cfg] is not None:
                    aniexists = yield \
                        self.Animals.find_one(
                            {'iid': self.input_data[animal_cfg]})
                    animal_org_iid = aniexists['organization_iid']
                    imageset_org_iid = objimgset['owner_organization_iid']
                    if animal_org_iid != imageset_org_iid:
                        # Request Verification
                        # Get emails from the
                        userslist = yield self.Users.find({'organization_iid': animal_org_iid}).to_list(None)
                        emails = [user['email'] for user in userslist]
                        orgname = yield self.db.organizations.find_one({'iid': int(imageset_org_iid)})
                        aniorg = yield self.db.organizations.find_one({'iid': int(aniexists['organization_iid'])})
                        if not orgname:
                            orgname = 'no name defined'
                        else:
                            orgname = orgname['name']
                        if len(emails) > 0:
                            for eaddr in emails:
                                msg = """From: %s\nTo: %s\nSubject: LINC Lion: Request for verification\n\nThis email was created by the system due to an association request of an image set with a lion from another organization.\nThe image set was associated with the lion:\n\nId: %s\nName: %s\nOrganization: %s\n\nThe image set is presented below:\n\nId: %s\nOrganization: %s\nLink: %s (accessible for previous logged users)\n\nPlease, go to the LINC website to verify (accept) or remove the request for association.\n\nLinc Lion Team\nhttps://linc.linclion.org/\n

                                """
                                msg = msg % (
                                    self.settings['EMAIL_FROM'],
                                    eaddr,
                                    aniexists['iid'],
                                    aniexists['name'],
                                    aniorg['name'],
                                    imageset_id,
                                    orgname,
                                    'https://linc.linclion.org/#/imageset/' + str(imageset_id))
                                pemail = yield Task(self.sendEmail, eaddr, msg)
                                info(pemail)
                if 'is_verified' in self.input_data.keys() and self.input_data['is_verified'] is True:
                    imgset2ver = yield self.ImageSets.find_one(query)
                    userslist = yield self.Users.find({'organization_iid': imgset2ver['owner_organization_iid']}).to_list(None)
                    animobj = yield self.Animals.find_one({'iid': imgset2ver['animal_iid']})
                    if animobj:
                        aniorg = yield self.db.organizations.find_one({'iid': animobj['organization_iid']})
                        imgorg = yield self.db.organizations.find_one({'iid': imgset2ver['owner_organization_iid']})
                        emails = [user['email'] for user in userslist]
                        if len(emails) > 0:
                            for eaddr in emails:
                                msg = """From: %s\nTo: %s\nSubject: LINC Lion: Image set %s was verified\n\nThis email was created by the system as a notification for the accept of an image set association with a lion from another organization.\nThe image set:\n\nId: %s\nOrganization: %s\nLink: %s (accessible for previous logged users)\n\nIt was associated with the lion:\n\nId: %s\nName: %s\nOrganization: %s\n
                                \nLinc Lion Team\nhttps://linc.linclion.org/\n

                                """
                                msg = msg % (
                                    self.settings['EMAIL_FROM'],
                                    eaddr,
                                    imageset_id,
                                    imageset_id,
                                    imgorg['name'],
                                    'https://linc.linclion.org/#/imageset/' + str(imageset_id),
                                    animobj['iid'],
                                    animobj['name'],
                                    aniorg['name'])
                                pemail = yield Task(self.sendEmail, eaddr, msg)
                                info(pemail)
                try:
                    imgid = ObjId(objimgset['_id'])
                    del objimgset['_id']
                    info(objimgset)
                    objimgset = ImageSet(objimgset)
                    objimgset.validate()
                    objimgset = objimgset.to_native()
                    # objimgset['_id'] = imgid
                    updnobj = yield \
                        self.ImageSets.update(
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
            imgobj = yield self.ImageSets.find_one(query)
            if imgobj:
                # check if it's a primary image set
                imgprim = yield self.Animals.find({}, {'primary_image_set_iid': 1}).to_list(None)
                imgprim = [int(x['primary_image_set_iid']) for x in imgprim]
                if int(imageset_id) in imgprim:
                    self.response(400, 'The image set ' + str(imageset_id) +
                                  ' is a primary one, it must be deleted through its ' + self.animal + '.')
                    return
                # 1 - Remove imaget set
                rmved = yield self.ImageSets.remove({'iid': imgobj['iid']})
                info(str(rmved))
                rem = yield Task(self.cache_remove, imgobj['iid'], 'imgset')
                info(rem)
                # 2 - Remove images of the image set
                imgl = yield self.Images.find({'image_set_iid': imgobj['iid']}).to_list(None)
                rmlist = list()
                for img in imgl:
                    # Remove joined referenced
                    resp = yield self.ImageSets.update({'main_image_iid': img['iid']}, {'$set': {'main_image_iid': None}})
                    info(resp)
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
                    rmladd = yield self.db.dellist.insert({'list': rmlist, 'ts': datetime.now()})
                    info(rmladd)
                rmved = yield self.Images.remove({'image_set_iid': imgobj['iid']}, multi=True)
                info(str(rmved))
                # 3 - Removing cvrequests and cvresults
                cvreql = yield self.CVRequests.find({'image_set_iid': imgobj['iid']}).to_list(None)
                for cvreq in cvreql:
                    # Removing cvresult
                    rmved = yield self.CVResults.remove({'cvrequest_iid': cvreq['iid']})
                    info(str(rmved))
                    # Removing cvrequest
                    rmved = yield self.CVRequests.remove({'_id': cvreq['_id']})
                    info(str(rmved))
            else:
                self.response(404, 'Image set not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')

    @asynchronous
    @engine
    def list(self, callback=None):
        current_user = yield self.Users.find_one({'email': self.current_user['username']})
        is_admin = current_user['admin']
        current_organization = yield self.db.organizations.find_one({'iid': current_user['organization_iid']})
        support_data = None
        output = list()
        cursor = self.ImageSets.find()
        while (yield cursor.fetch_next):
            obj = cursor.next_object()
            imgsetcache = yield Task(self.cache_read, obj['iid'], 'imgset')
            if imgsetcache:
                output.append(imgsetcache.copy())
            else:
                # prepare data
                if not support_data:
                    support_data = yield Task(self.get_support_data)
                    # animals = support_data['animals']
                    primary_imgsets_list = support_data['primary_imgsets_list'].copy()
                    animals_names = support_data['animals_names']
                    dead_dict = support_data['dead_dict']
                    support_data = True
                imgset_obj = dict()
                imgset_obj['obj_id'] = str(obj['_id'])
                imgset_obj['id'] = obj['iid']
                imgset_obj[self.animals + '_org_id'] = ''
                if obj['animal_iid']:
                    imgset_obj['name'] = animals_names[obj['animal_iid']]
                    imgset_obj['dead'] = dead_dict[obj['animal_iid']]
                    imgset_obj[self.animal + '_id'] = obj['animal_iid']
                    animal_org_iid = yield self.Animals.find_one({'iid': obj['animal_iid']})
                    if animal_org_iid:
                        imgset_obj[self.animals + '_org_id'] = animal_org_iid['organization_iid']
                else:
                    imgset_obj['name'] = '-'
                    imgset_obj['dead'] = None
                    imgset_obj[self.animal + '_id'] = None

                obji = yield self.Images.find_one({'iid': obj['main_image_iid']})
                if obji:
                    imgset_obj['thumbnail'] = self.settings['S3_URL'] + obji['url'] + '_icon.jpg'
                    imgset_obj['image'] = self.settings['S3_URL'] + obji['url'] + '_medium.jpg'
                else:
                    obji = yield self.Images.find({'image_set_iid': obj['iid']}).to_list(None)
                    if len(obji) > 0:
                        imgset_obj['thumbnail'] = self.settings['S3_URL'] + obji[0]['url'] + '_icon.jpg'
                        imgset_obj['image'] = self.settings['S3_URL'] + obji[0]['url'] + '_medium.jpg'
                    else:
                        imgset_obj['thumbnail'] = ''
                        imgset_obj['image'] = ''

                if obj['date_of_birth']:
                    imgset_obj['age'] = self.age(born=obj['date_of_birth'])
                    imgset_obj['date_of_birth'] = obj['date_of_birth'].date().isoformat()
                else:
                    imgset_obj['age'] = '-'
                    imgset_obj['date_of_birth'] = '-'

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

                if 'notes' in obj.keys():
                    imgset_obj['notes'] = obj['notes']
                else:
                    imgset_obj['notes'] = ''

                if obj['owner_organization_iid']:
                    objo = yield self.db.organizations.find_one({'iid': obj['owner_organization_iid']})
                    if objo:
                        imgset_obj['organization'] = objo['name']
                        imgset_obj['organization_id'] = obj['owner_organization_iid']
                    else:
                        imgset_obj['organization'] = '-'
                        imgset_obj['organization_id'] = '-'

                imgset_obj['gender'] = obj['gender']
                imgset_obj['is_verified'] = obj['is_verified']
                imgset_obj['is_primary'] = (obj['iid'] in primary_imgsets_list)

                can_show = (True if (is_admin or current_organization['iid'] == imgset_obj['organization_id']) else False) if imgset_obj['geopos_private'] else True
                if can_show:
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
                else:
                    imgset_obj['latitude'] = None
                    imgset_obj['longitude'] = None
                    imgset_obj['tag_location'] = None

                objcvreq = yield self.CVRequests.find_one({'image_set_iid': obj['iid']})
                if objcvreq:
                    imgset_obj['cvrequest'] = str(objcvreq['_id'])
                    imgset_obj['req_status'] = objcvreq['status']
                else:
                    imgset_obj['cvrequest'] = None
                    imgset_obj['req_status'] = None

                imgset_obj['cvresults'] = None
                if objcvreq:
                    objcvres = yield self.CVResults.find_one({'cvrequest_iid': objcvreq['iid']})
                    if objcvres:
                        imgset_obj['cvresults'] = str(objcvres['_id'])
                output.append(imgset_obj)
                addcache = yield Task(self.cache_set, obj['iid'], 'imgset', imgset_obj, None)
                info(addcache)
        callback(output)

    @engine
    def get_support_data(self, callback=None):
        animals = yield self.Animals.find().to_list(None)
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
        output = {
            'animals': animals,
            'primary_imgsets_list': primary_imgsets_list.copy(),
            'animals_names': animals_names,
            'dead_dict': dead_dict
        }
        callback(output)


class ImageSetsCheckReqHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET')

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, imageset_id=None, cvrequirements=None):
        info(cvrequirements)
        try:
            imageset_id = int(imageset_id)
        except Exception as e:
            imageset_id = None
        if not imageset_id:
            self.response(400, 'Invalid request')
        else:
            resp_cv = 0
            resp_wh = 0
            try:
                resp_cv = yield self.Images.find({'image_tags': ['cv'], 'image_set_iid': imageset_id}).count()
                resp_wh = yield self.Images.find(
                    {'$or': [
                        {'image_tags': ['whisker']},
                        {'image_tags': ['whisker-left']},
                        {'image_tags': ['whisker-right']}], 'image_set_iid': imageset_id}).count()
            except Exception as e:
                info(e)
            output = {
                'cv': bool(resp_cv),
                'whisker': bool(resp_wh)
            }
            # api(self, url, method, body=None, headers=None,
            # auth_username=None, auth_password=None, callback=None):
            output['cv_lion_list'] = []
            output['whisker_lion_list'] = []
            if any(output.values()):
                try:
                    resp = yield Task(
                        self.api,
                        url=self.settings['CVSERVER_URL'] + '/linc/v1/capabilities',
                        method='GET',
                        headers={'ApiKey': self.settings['CV_APIKEY']})
                    if resp.code == 200 and output['cv']:
                        output['cv_lion_list'] = [int(x) for x in loads(resp.body.decode('utf-8'))['valid_cv_lion_ids']]
                    if resp.code == 200 and output['whisker']:
                        output['whisker_lion_ids'] = [int(x) for x in loads(resp.body.decode('utf-8'))['valid_whisker_lion_ids']]
                except Exception as e:
                    info(e)
                    info('Fail to retrieve classifier capabilities.')
            self.response(200, 'Requirements checked for image set = {}.'.format(imageset_id), output)

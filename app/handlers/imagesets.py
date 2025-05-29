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

    @api_authenticated
    async def get(self, imageset_id=None, param=None):
        if param == 'cvrequest':
            self.response(
                400, 'CV requests are accepted if they are sent by POST method.')
            return
        current_user = await self.Users.find_one({'email': self.current_user['username']})
        if not current_user:
            self.response(401, 'Authentication required.')
            return
        is_admin = current_user['admin']
        current_organization = await self.db.organizations.find_one({'iid': current_user['organization_iid']})
        if imageset_id == 'list':
            output = await self.list()
            self.response(200, 'Image sets list.', output)
        elif imageset_id and param == 'profile':
            query = self.query_id(imageset_id)
            imgset = await self.ImageSets.find_one(query)
            if imgset:
                imgprim = await self.Animals.find({}, {'primary_image_set_iid': 1}).to_list(None)
                imgprim = [x['primary_image_set_iid'] for x in imgprim]
                output = imgset
                output['geopos_private'] = imgset.get('geopos_private', False)
                output['obj_id'] = str(imgset['_id'])
                del output['_id']
                self.switch_iid(output)
                org = await self.db.organizations.find_one({'iid': output['owner_organization_iid']})
                if org:
                    output['organization'] = org['name']
                    output['organization_id'] = org['iid']
                else:
                    output['organization'] = '-'
                    output['organization_id'] = '-'
                if output['id'] in imgprim:
                    output['is_primary'] = True
                    queryani = {'primary_image_set_iid': output['id']}
                else:
                    output['is_primary'] = False
                    queryani = {'iid': output['animal_iid']}
                animalobj = await self.Animals.find_one(queryani)
                if animalobj:
                    output['name'] = animalobj['name']
                    output['dead'] = animalobj.get('dead', False)
                else:
                    output['name'] = '-'
                    output['dead'] = None
                if output.get('date_of_birth'):
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

                img = await self.Images.find_one({'iid': output['main_image_id']})
                if img:
                    output['image'] = await self.imgurl(img['url'], 'thumbnail')
                    output['thumbnail'] = await self.imgurl(img['url'], 'icon')
                else:
                    img = await self.Images.find({'image_set_iid': output['id']}).to_list(None)
                    if img:
                        output['image'] = await self.imgurl(img[0]['url'], 'thumbnail')
                        output['thumbnail'] = await self.imgurl(img[0]['url'], 'icon')
                    else:
                        output['image'] = ''
                        output['thumbnail'] = ''
                can_show = is_admin or current_organization['iid'] == org['iid'] if output['geopos_private'] else True
                if can_show:
                    if output['location']:
                        output['latitude'] = output['location'][0][0]
                        output['longitude'] = output['location'][0][1]
                    else:
                        output['latitude'] = None
                        output['longitude'] = None
                    output.setdefault('tag_location', None)
                else:
                    output['latitude'] = None
                    output['longitude'] = None
                    output['tag_location'] = None
                del output['location']

                info(output['id'])
                cvreq = await self.CVRequests.find_one({'image_set_iid': output['id']})
                info(cvreq)
                if cvreq:
                    output['cvrequest'] = str(cvreq['_id'])
                    output['req_status'] = cvreq['status']
                    cvres = await self.CVResults.find_one({'cvrequest_iid': cvreq['iid']})
                    output['cvresults'] = str(cvres['_id']) if cvres else None
                else:
                    output['req_status'] = None
                    output['cvrequest'] = None
                    output['cvresults'] = None
                output[self.animals + '_org_id'] = ''
                if output['animal_iid']:
                    animal_org_iid = await self.Animals.find_one({'iid': output['animal_iid']})
                    if animal_org_iid:
                        output[self.animals + '_org_id'] = animal_org_iid['organization_iid']
                output[self.animal + '_id'] = output['animal_iid']
                del output['animal_iid']

                self.response(200, 'Imageset found.', output)
                return
            else:
                self.response(404, 'Imageset not found.')
                return
        elif imageset_id and param == 'gallery':
            query = self.query_id(imageset_id)
            objimgset = await self.ImageSets.find_one(query)
            if objimgset:
                # Check if is Primary Imageset
                imgprim = await self.Animals.find_one({'iid': objimgset['animal_iid']}, {'primary_image_set_iid': 1})
                is_primary = False
                if imgprim and imgprim['primary_image_set_iid'] == objimgset['animal_iid']:
                    is_primary = True
                images = await self.Images.find(
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
                        vjoined = (img['joined'] > 0)
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
                        if 'date_stamp' in exifd.keys() and exifd['date_stamp']:
                            imgout['date_stamp'] = datetime.strptime(
                                exifd['date_stamp'], '%Y-%m-%dT%H:%M:%S').date().isoformat()
                    for suf in ['icon', 'medium', 'thumbnail']:
                        imgout[suf] = await self.imgurl(img['url'], suf)
                    imgout['cover'] = (img['iid'] == cover)
                    output['images'].append(imgout)
                self.response(200, 'Gallery images for the image set ' + str(imageset_id) + '.', output)
            else:
                self.response(404, 'Imageset not found.')
            return

    @api_authenticated
    async def post(self, imageset_id=None, cvrequest=None):
        if not imageset_id:
            response = await self.create_imageset(self.input_data)
            if response and response['code'] != 201:
                self.response(response['code'], response['message'])
                return
            self.set_status(201)
            self.finish(self.json_encode({'status': 'success', 'message': response['message'], 'data': response['data']}))
        else:
            query = self.query_id(imageset_id)
            imgchk = await self.ImageSets.find_one(query)
            if imgchk:
                if self.animals not in self.input_data.keys():
                    self.response(400, 'The cvrequest needs a list of ' + self.settings[
                                  'animals'] + ' id like: { "' + self.animals + '": [<id>,...] }.')
                    return
                if cvrequest:
                    cvreqchk = await self.CVRequests.find_one({'image_set_iid': int(imageset_id)})
                    if cvreqchk:
                        if cvreqchk['status'] == 'error':
                            info('Removing old CV Request of the image set {} that was marked with error.'.format(imageset_id))
                            await self.CVRequests.delete_one({'iid': cvreqchk['iid']})
                        else:
                            self.response(
                                409,
                                'A request for indentification of this imageset already exists in the database.')
                            return
                    check_algo = {'cv': False, 'whisker': False}
                    classl = self.input_data.get('classifier', [])
                    for v in ['cv', 'whisker']:
                        check_algo[v] = v in classl
                    if not any(check_algo.values()):
                        self.response(400, 'Request invalid, please select at least one algorithm.')
                        return
                    request_base_body = dict()
                    request_base_body['classifiers'] = check_algo
                    request_base_body['age'] = self.age(imgchk['date_of_birth']) if imgchk['date_of_birth'] else None
                    request_base_body['gender'] = imgchk['gender']
                    animalscheck = await self.Animals.find({'iid': {'$in': self.input_data[self.animals]}}).to_list(None)
                    if not animalscheck:
                        self.response(400, 'No id valid in the list of ' +
                                      self.animals + ' passed.')
                        return
                    lanimals = [x['iid'] for x in animalscheck]
                    info('List passed: {}'.format(self.input_data[self.animals]))
                    info('List found : {}'.format(lanimals))
                    request_base_body[self.animals + '_found'] = lanimals
                    request_base_body[self.animals + '_submitted'] = self.input_data[self.animals]
                    cv_imgs = await self.Images.find(
                        {'image_tags': ['cv'],
                         'image_set_iid': imgchk['iid']}).to_list(None)
                    wh_imgs = await self.Images.find(
                        {'$or': [
                            {'image_tags': ['whisker-left']},
                            {'image_tags': ['whisker-right']}],
                         'image_set_iid': imgchk['iid']}).to_list(None)
                    cv_calls = list()
                    info(check_algo)
                    if check_algo.get('cv', False):
                        for x in cv_imgs:
                            cv_calls.append({
                                'type': 'cv',
                                'url': await self.imgurl(x['url'], "full")
                            })
                    wh_calls = list()
                    if check_algo.get('whisker', False):
                        for x in wh_imgs:
                            wh_calls.append({
                                'type': 'whisker',
                                'url': await self.imgurl(x['url'], "full")
                            })
                    if cv_calls or wh_calls:
                        request_base_body['cv_calls'] = cv_calls if cv_calls else []
                        request_base_body['whisker_calls'] = wh_calls if wh_calls else []
                        newobj = dict()
                        newobj['iid'] = await self.new_iid(CVRequest.collection())
                        newobj['requesting_organization_iid'] = self.current_user['org_id']
                        newobj['image_set_iid'] = imageset_id
                        newobj['status'] = 'created'
                        newobj['request_body'] = dumps(request_base_body)
                        try:
                            newsaved = CVRequest(newobj)
                            newsaved.validate()
                            result = await self.CVRequests.insert_one(newsaved.to_native())
                            newreqadd = result.inserted_id
                        except Exception as e:
                            info(e)
                            self.response(500, 'Fail to create the CV Request.')
                            return
                        rem = await self.cache_remove(str(imageset_id), 'imgset')
                        info(rem)
                        output = newsaved.to_native()
                        output['obj_id'] = str(newreqadd)
                        self.switch_iid(output)
                        del output['request_body']
                        output['requesting_organization_id'] = output['requesting_organization_iid']
                        del output['requesting_organization_iid']
                        output['image_set_id'] = output['image_set_iid']
                        del output['image_set_iid']
                        self.response(201, 'CV request created.', output)
                    else:
                        self.response(400, 'The image set does not have images with the tags cv or whisker.')
                else:
                    self.response(400, 'Invalid request.')
            else:
                self.response(404, 'Image set id not found.')

    @api_authenticated
    async def put(self, imageset_id=None):
        # update an imageset
        if imageset_id:
            # Clear cache for the imageset_id
            rem = await self.cache_remove(str(imageset_id), 'imgset')
            info(rem)
            # getting the object
            query = self.query_id(imageset_id)
            objimgset = await self.ImageSets.find_one(query)
            if objimgset:
                dt = datetime.now()
                objimgset['updated_at'] = dt
                fields_allowed = ['uploading_user_id', 'uploading_organization_id', 'owner_organization_id',
                                  'is_verified', 'latitude', 'longitude', 'tag_location', 'gender', 'date_of_birth',
                                  'tags', 'date_stamp', 'notes', self.animal + '_id', 'main_image_id', 'geopos_private']
                update_data = dict()
                animal_cfg = self.animal + '_id'
                if animal_cfg in self.input_data.keys():
                    if self.input_data[animal_cfg] is None:
                        assocanimalid = objimgset['animal_iid']
                        primimgsetid = await self.Animals.find_one({'iid': assocanimalid})
                        if primimgsetid:
                            primimgsetid = primimgsetid['primary_image_set_iid']
                            resp = await self.Images.update_many(
                                {'$and': [{'image_set_iid': objimgset['iid']},
                                          {'joined': {'$ne': 0}}]},
                                {'$set': {'joined': 0}})
                            info(resp)
                            imgslist = await self.Images.find({'image_set_iid': objimgset['iid']}).to_list(None)
                            imgslist = [int(x['iid']) for x in imgslist]
                            resp = await self.ImageSets.update_many(
                                {'main_image_iid': {'$in': imgslist}}, {'$set': {'main_image_iid': None}})
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
                                objimgset['animal_iid'] = update_data[self.animal + '_id']
                                del objimgset[self.animal + '_iid']
                            del update_data[field]
                            continue
                        elif field in ['date_stamp', 'date_of_birth']:
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
                        objimgset[field] = update_data[field]

                useriid = objimgset['uploading_user_iid']
                userexists = await self.Users.find_one({'iid': useriid})
                if not userexists:
                    self.response(409, "Uploading user id referenced doesn't exist.")
                    return
                orgiid = objimgset['uploading_organization_iid']
                orgexists = await self.db.organizations.find_one({'iid': orgiid})
                if not orgexists:
                    self.response(409, "Uploading organization id referenced doesn't exist.")
                    return
                oorgiid = objimgset['owner_organization_iid']
                oorgexists = await self.db.organizations.find_one({'iid': oorgiid})
                if oorgexists['iid'] != oorgiid:
                    self.response(409, "Owner organization id referenced doesn't exist.")
                    return
                if objimgset['animal_iid']:
                    aniexists = await self.Animals.find_one({'iid': objimgset['animal_iid']})
                    if aniexists['iid'] != objimgset['animal_iid']:
                        self.response(409, 'The ' + self.animal + " id sent doesn't exist.")
                        return
                if animal_cfg in self.input_data.keys() and self.input_data[animal_cfg] is not None:
                    aniexists = await self.Animals.find_one({'iid': self.input_data[animal_cfg]})
                    animal_org_iid = aniexists['organization_iid']
                    imageset_org_iid = objimgset['owner_organization_iid']
                    if animal_org_iid != imageset_org_iid:
                        userslist = await self.Users.find({'organization_iid': animal_org_iid}).to_list(None)
                        emails = [user['email'] for user in userslist]
                        orgname = await self.db.organizations.find_one({'iid': int(imageset_org_iid)})
                        aniorg = await self.db.organizations.find_one({'iid': int(aniexists['organization_iid'])})
                        orgname = orgname['name'] if orgname else 'no name defined'
                        if len(emails) > 0:
                            for eaddr in emails:
                                msg = """From: %s\nTo: %s\nSubject: LINC Lion: Request for verification\n\nThis email was created by the system due to an association request of an image set with a lion from another organization.\nThe image set was associated with the lion:\n\nId: %s\nName: %s\nOrganization: %s\n\nThe image set is presented below:\n\nId: %s\nOrganization: %s\nLink: %s (accessible for previous logged users)\n\nPlease, go to the LINC website to verify (accept) or remove the request for association.\n\nLinc Lion Team\nhttps://linc.linclion.org/\n
                                """ % (
                                    self.settings['EMAIL_FROM'],
                                    eaddr,
                                    aniexists['iid'],
                                    aniexists['name'],
                                    aniorg['name'],
                                    imageset_id,
                                    orgname,
                                    'https://linc.linclion.org/#/imageset/' + str(imageset_id))
                                pemail = await self.sendEmail(eaddr, msg)
                                info(pemail)
                if 'is_verified' in self.input_data.keys() and self.input_data['is_verified'] is True:
                    imgset2ver = await self.ImageSets.find_one(query)
                    userslist = await self.Users.find({'organization_iid': imgset2ver['owner_organization_iid']}).to_list(None)
                    animobj = await self.Animals.find_one({'iid': imgset2ver['animal_iid']})
                    if animobj:
                        aniorg = await self.db.organizations.find_one({'iid': animobj['organization_iid']})
                        imgorg = await self.db.organizations.find_one({'iid': imgset2ver['owner_organization_iid']})
                        emails = [user['email'] for user in userslist]
                        if len(emails) > 0:
                            for eaddr in emails:
                                msg = """From: %s\nTo: %s\nSubject: LINC Lion: Image set %s was verified\n\nThis email was created by the system as a notification for the accept of an image set association with a lion from another organization.\nThe image set:\n\nId: %s\nOrganization: %s\nLink: %s (accessible for previous logged users)\n\nIt was associated with the lion:\n\nId: %s\nName: %s\nOrganization: %s\n
                                \nLinc Lion Team\nhttps://linc.linclion.org/\n
                                """ % (
                                    self.settings['EMAIL_FROM'],
                                    eaddr,
                                    imageset_id,
                                    imageset_id,
                                    imgorg['name'],
                                    'https://linc.linclion.org/#/imageset/' + str(imageset_id),
                                    animobj['iid'],
                                    animobj['name'],
                                    aniorg['name'])
                                pemail = await self.sendEmail(eaddr, msg)
                                info(pemail)
                try:
                    imgid = ObjId(objimgset['_id'])
                    del objimgset['_id']
                    info(objimgset)
                    objimgset = ImageSet(objimgset)
                    objimgset.validate()
                    objimgset = objimgset.to_native()
                    updnobj = await self.ImageSets.update_one(
                        {'_id': imgid}, 
                        {'$set': objimgset}, 
                        upsert=True
                    )
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
                    self.finish(self.json_encode({'status': 'success', 'message': 'Image set updated.', 'data': output}))
                except ValidationError as e:
                    self.response(400, "Invalid input data. Error: " + str(e) + '.')
                    return
            else:
                self.response(404, 'Imageset id not found.')
        else:
            self.response(400, 'Update requests (PUT) must have a resource ID and update pairs for key and value.')


    @api_authenticated
    async def delete(self, imageset_id=None):
        # delete an imageset
        if imageset_id:
            query = self.query_id(imageset_id)
            imgobj = await self.ImageSets.find_one(query)
            if imgobj:
                # check if it's a primary image set
                imgprim = await self.Animals.find({}, {'primary_image_set_iid': 1}).to_list(None)
                imgprim = [int(x['primary_image_set_iid']) for x in imgprim]
                if int(imageset_id) in imgprim:
                    self.response(400, 'The image set ' + str(imageset_id) +
                                  ' is a primary one, it must be deleted through its ' + self.animal + '.')
                    return
                # 1 - Remove image set
                rmved = await self.ImageSets.delete_one({'iid': imgobj['iid']})
                info(str(rmved))
                rem = await self.cache_remove(imgobj['iid'], 'imgset')
                info(rem)
                # 2 - Remove images of the image set
                imgl = await self.Images.find({'image_set_iid': imgobj['iid']}).to_list(None)
                rmlist = list()
                for img in imgl:
                    # Remove joined referenced
                    resp = await self.ImageSets.update_one(
                        {'main_image_iid': img['iid']}, 
                        {'$set': {'main_image_iid': None}}
                    )
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
                    result = await self.db.dellist.insert_one({'list': rmlist, 'ts': datetime.now()})
                    info(result)
                rmved = await self.Images.delete_many({'image_set_iid': imgobj['iid']})
                info(str(rmved))
                # 3 - Removing cvrequests and cvresults
                cvreql = await self.CVRequests.find({'image_set_iid': imgobj['iid']}).to_list(None)
                for cvreq in cvreql:
                    # Removing cvresult
                    rmved = await self.CVResults.delete_one({'cvrequest_iid': cvreq['iid']})
                    info(str(rmved))
                    # Removing cvrequest
                    rmved = await self.CVRequests.delete_one({'_id': cvreq['_id']})
                    info(str(rmved))
                self.response(200, 'Image set deleted.')
            else:
                self.response(404, 'Image set not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')


    async def list(self):
        current_user = await self.Users.find_one({'email': self.current_user['username']})
        is_admin = current_user['admin']
        current_organization = await self.db.organizations.find_one({'iid': current_user['organization_iid']})
        support_data = None
        output = list()
        cursor = self.ImageSets.find()
        while (await cursor.fetch_next):
            obj = cursor.next_object()
            imgsetcache = await self.cache_read(obj['iid'], 'imgset')
            if imgsetcache:
                output.append(imgsetcache.copy())
            else:
                if not support_data:
                    support_data = await self.get_support_data()
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
                    animal_org_iid = await self.Animals.find_one({'iid': obj['animal_iid']})
                    if animal_org_iid:
                        imgset_obj[self.animals + '_org_id'] = animal_org_iid['organization_iid']
                else:
                    imgset_obj['name'] = '-'
                    imgset_obj['dead'] = None
                    imgset_obj[self.animal + '_id'] = None

                obji = await self.Images.find_one({'iid': obj['main_image_iid']})
                if obji:
                    imgset_obj['thumbnail'] = await self.imgurl(obji['url'], 'icon')
                    imgset_obj['image'] = await self.imgurl(obji['url'], 'medium')
                else:
                    obji = await self.Images.find({'image_set_iid': obj['iid']}).to_list(None)
                    if len(obji) > 0:
                        imgset_obj['thumbnail'] = await self.imgurl(obji[0]['url'], 'icon')
                        imgset_obj['image'] = await self.imgurl(obji[0]['url'], 'medium')
                    else:
                        imgset_obj['thumbnail'] = ''
                        imgset_obj['image'] = ''

                if obj['date_of_birth']:
                    imgset_obj['age'] = self.age(born=obj['date_of_birth'])
                    imgset_obj['date_of_birth'] = obj['date_of_birth'].date().isoformat()
                else:
                    imgset_obj['age'] = '-'
                    imgset_obj['date_of_birth'] = '-'

                imgset_obj['date_stamp'] = obj['date_stamp'] if obj['date_stamp'] else '-'
                imgset_obj['tags'] = obj['tags'] if obj['tags'] else None
                imgset_obj['geopos_private'] = obj.get('geopos_private', False)
                imgset_obj['joined'] = obj.get('joined', [])
                imgset_obj['notes'] = obj.get('notes', '')

                if obj['owner_organization_iid']:
                    objo = await self.db.organizations.find_one({'iid': obj['owner_organization_iid']})
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
                    imgset_obj['tag_location'] = obj.get('tag_location', None)
                else:
                    imgset_obj['latitude'] = None
                    imgset_obj['longitude'] = None
                    imgset_obj['tag_location'] = None

                objcvreq = await self.CVRequests.find_one({'image_set_iid': obj['iid']})
                if objcvreq:
                    imgset_obj['cvrequest'] = str(objcvreq['_id'])
                    imgset_obj['req_status'] = objcvreq['status']
                    objcvres = await self.CVResults.find_one({'cvrequest_iid': objcvreq['iid']})
                    if objcvres and objcvreq['status'] in ['finished', 'error']:
                        imgset_obj['cvresults'] = str(objcvres['_id'])
                    else:
                        imgset_obj['cvresults'] = None
                else:
                    imgset_obj['cvrequest'] = None
                    imgset_obj['req_status'] = None
                    imgset_obj['cvresults'] = None

                output.append(imgset_obj)
                addcache = await self.cache_set(obj['iid'], 'imgset', imgset_obj, None)
                info(addcache)
        return output

    async def get_support_data(self, callback=None):
        animals = await self.Animals.find().to_list(None)
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

    @api_authenticated
    async def get(self, imageset_id=None, cvrequirements=None):
        info(cvrequirements)
        try:
            imageset_id = int(imageset_id)
        except Exception as e:
            imageset_id = None
        if not imageset_id:
            self.response(400, 'Invalid request')
        else:
            cvreqchk = await self.CVRequests.find_one({'image_set_iid': imageset_id})
            if cvreqchk:
                if cvreqchk['status'] != 'error':
                    self.response(
                        409,
                        'A previous request for indentification of this image set already exists in the database.',
                        {'cv_request_id': cvreqchk['iid'], 'status': cvreqchk['status']})
                    return
            resp_cv = await self.Images.count_documents({'image_tags': 'cv', 'image_set_iid': imageset_id})
            resp_wh = await self.Images.count_documents(
                {'$or': [{'image_tags': 'whisker-left'},
                {'image_tags': 'whisker-right'}], 'image_set_iid': imageset_id})
            output = {
                'cv': bool(resp_cv),
                'whisker': bool(resp_wh)
            }
            output['cv_lion_list'] = []
            output['whisker_lion_list'] = []
            if any(output.values()):
                try:
                    resp = await self.api(
                        url=self.settings['CVSERVER_URL'] + '/linc/v1/capabilities',
                        method='GET',
                        headers={'ApiKey': self.settings['CV_APIKEY']})
                    if resp.code == 200 and output['cv']:
                        output['cv_lion_list'] = [int(x) for x in loads(resp.body.decode('utf-8'))['valid_cv_lion_ids']]
                    if resp.code == 200 and output['whisker']:
                        output['whisker_lion_list'] = [int(x) for x in loads(resp.body.decode('utf-8'))['valid_whisker_lion_ids']]
                except Exception as e:
                    info(e)
                    info('Fail to retrieve classifier capabilities.')
            self.response(200, 'Requirements checked for image set = {}.'.format(imageset_id), output)

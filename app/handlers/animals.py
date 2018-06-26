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

from tornado.web import asynchronous
from tornado.gen import coroutine, engine, Task
from handlers.base import BaseHandler
from models.animal import Animal
from models.imageset import ImageSet
from datetime import datetime, time
from bson import ObjectId as ObjId
from pymongo import DESCENDING
from lib.rolecheck import api_authenticated
from schematics.exceptions import ValidationError
from logging import info
from json import loads, dumps


class AnimalsHandler(BaseHandler):
    """A class that handles requests about animals informartion."""
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, animal_id=None, xurl=None):

        current_user = yield self.Users.find_one(
            {'email': self.current_user['username'] if self.current_user and 'username' in self.current_user else None})
        is_admin = current_user['admin']
        current_organization = yield self.db.organizations.find_one({'iid': current_user['organization_iid']})

        apiout = self.get_argument('api', None)
        noimages = self.get_argument('no_images', '')
        if noimages.lower() == 'true':
            noimages = True
        else:
            noimages = False
        if animal_id:
            if animal_id == 'list':
                org_filter = self.get_argument('org_id', None)
                query_ani = {}
                query_org = {}
                if org_filter:
                    query_ani = {'organization_iid': int(org_filter)}
                    query_org = {'iid': int(org_filter)}
                objs = yield self.Animals.find(query_ani).to_list(None)
                orgs = yield self.db.organizations.find(query_org).to_list(None)
                orgnames = dict()
                for org in orgs:
                    orgnames[org['iid']] = org['name']
                if len(objs) > 0:
                    output = yield Task(self.list, objs, orgnames)
                    self.response(200, 'Success.', output)
                else:
                    self.response(404, 'Not found.')
                return
                # self.set_status(200)
                # self.finish(self.json_encode({'status': 'success', 'data':output}))
            elif animal_id and xurl == 'profile':
                # show profile page data for the website
                query = self.query_id(animal_id)
                objanimal = yield self.Animals.find_one(query)
                if objanimal:
                    output = objanimal
                    output['obj_id'] = str(objanimal['_id'])
                    del output['_id']
                    self.switch_iid(output)
                    output['organization_id'] = output['organization_iid']
                    del output['organization_iid']
                    output['primary_image_set_id'] = output['primary_image_set_iid']
                    del output['primary_image_set_iid']
                    if 'dead' not in output.keys():
                        output['dead'] = False
                    # Get organization name
                    org = yield self.db.organizations.find_one({'iid': output['organization_id']})
                    if org:
                        output['organization'] = org['name']
                    else:
                        output['organization'] = '-'

                    # get data from the primary image set
                    objimgset = yield self.ImageSets.find_one(
                        {'iid': objanimal['primary_image_set_id']})
                    if not objimgset:
                        objimgsets = yield self.ImageSets.find(
                            {'animal_iid': objanimal['iid']})
                        if len(objimgsets) > 0:
                            objimgset = objimgsets[0]
                        else:
                            objimgset = ImageSet().to_native()
                    exclude = ['_id', 'iid', 'animal_iid']
                    for k, v in objimgset.items():
                        if k not in exclude:
                            output[k] = v
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
                        output['image'] = ''
                        output['thumbnail'] = ''

                    # Geo Position Private
                    if 'geopos_private' not in output.keys():
                        output['geopos_private'] = False

                    can_show = (True if (is_admin or current_organization['iid'] == output['organization_id']) else False) if output['geopos_private'] else True
                    if can_show:
                        # Location
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

                    # Check verified
                    ivcquery = {'animal_iid': output['id'],
                                'is_verified': False,
                                'iid': {"$ne": output['primary_image_set_id']}}
                    ivc = yield self.ImageSets.find(ivcquery).count()
                    if ivc == 0:
                        output['is_verified'] = True
                    else:
                        output['is_verified'] = False
                    self.response(200, self.animal + ' found', output)
                    return
                else:
                    self.response(404, 'No ' + self.animal + ' can be found with the id = ' + animal_id + '.')
                    return
            elif animal_id and xurl == 'locations':
                try:
                    iid = int(animal_id)
                except Exception as e:
                    self.response(
                        400,
                        'Requests about locations only accept integer id for the %s.' % (self.animals))
                    return
                lname = yield self.Animals.find_one({'iid': iid}, {'name': 1})
                cursor = self.ImageSets.find(
                    {'animal_iid': iid},
                    {'iid': 1, 'location': 1,
                     'tag_location': 1, 'date_stamp': 1, 'updated_at': 1,
                     'geopos_private': 1, 'owner_organization_iid': 1})
                cursor.sort('updated_at', DESCENDING)
                imgsets = yield cursor.to_list(None)
                locations = list()
                litems = len(imgsets)
                if imgsets:
                    for i in imgsets:
                        # info(i)
                        if i['location']:
                            if 'geopos_private' not in i.keys():
                                geop = False
                            else:
                                geop = i['geopos_private']

                            can_show = (True if (is_admin or current_organization['iid'] == i['owner_organization_iid']) else False) if geop else True
                            if can_show:
                                latitude = i['location'][0][0]
                                longitude = i['location'][0][1]
                                if 'tag_location' in i.keys():
                                    tag_location = i['tag_location']
                                else:
                                    tag_location = None
                            else:
                                latitude = None
                                longitude = None
                                tag_location = None

                            locations.append(
                                {'id': i['iid'], 'label': 'Image Set ' + str(i['iid']), 'name': lname['name'],
                                 'latitude': latitude, 'longitude': longitude, 'tag_location': tag_location,
                                 'updated_at': i['updated_at'].date().isoformat(), 'date_stamp': i['date_stamp'],
                                 'geopos_private': geop, 'organization_id': i['owner_organization_iid']})
                self.response(200, 'Location list.', {'count': litems, 'locations': locations})
                return
            else:
                # return a specific animal accepting as id the integer id, hash and name
                query = self.query_id(animal_id)
                objs = yield self.Animals.find_one(query)
                if objs:
                    if 'dead' not in objs.keys():
                        objs['dead'] = False
                    if apiout:
                        objanimal = objs
                        self.switch_iid(objanimal)
                        objanimal['obj_id'] = objs['_id']
                        del objanimal['_id']
                        objanimal['organization_id'] = objanimal['organization_iid']
                        del objanimal['organization_iid']
                        objanimal['primary_image_set_id'] = objanimal['primary_image_set_iid']
                        del objanimal['primary_image_set_iid']
                    else:
                        objanimal = yield Task(self.prepare_output, objs, noimages)
                    self.set_status(200)
                    self.finish(self.json_encode(objanimal))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status': 'error', 'message': 'Not found.'}))
        else:
            # return a list of animals
            queryfilter = dict()
            filtersaccepted = ['gender', 'organization_id', 'dob_start', 'dob_end']
            for k, v in self.request.arguments.items():
                if k in filtersaccepted:
                    queryfilter[k] = self.get_argument(k)
            if 'organization_id' in queryfilter.keys():
                queryfilter['owner_organization_iid'] = int(queryfilter['organization_id'])
                del queryfilter['organization_id']
            try:
                if 'dob_start' in queryfilter.keys() or 'dob_end' in queryfilter.keys():
                    queryfilter['date_of_birth'] = dict()
                    if 'dob_start' in queryfilter.keys():
                        queryfilter['date_of_birth']["$gte"] = datetime.combine(
                            datetime.strptime(queryfilter['dob_start'], "%Y-%m-%d").date(), time.min)
                        del queryfilter['dob_start']
                    if 'dob_end' in queryfilter.keys():
                        queryfilter['date_of_birth']['$lte'] = datetime.combine(
                            datetime.strptime(queryfilter['dob_end'], "%Y-%m-%d").date(), time.min)
                        del queryfilter['dob_end']
            except Exception as e:
                self.response(400, 'Invalid value for dob_start/dob_end. Error: ' + str(e) + '.')
                return
            info(queryfilter)
            objs = yield self.ImageSets.find(queryfilter).to_list(None)
            iids = [x['animal_iid'] for x in objs]
            iids = list(set(iids))
            objs = yield self.Animals.find({'iid': {'$in': iids}}).to_list(None)
            output = list()
            for x in objs:
                if 'dead' not in x.keys():
                    x['dead'] = False
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
                    obj = yield Task(self.prepare_output, x, noimages)
                output.append(obj)
            self.set_status(200)
            if apiout:
                outshow = {'status': 'success', 'data': output}
            else:
                outshow = output
            self.finish(self.json_encode(outshow))

    @asynchronous
    @engine
    @api_authenticated
    def post(self):
        # create a new animal and imageset
        # parse data recept by POST and get only fields of the object
        animal = dict()
        if 'lion' in self.input_data.keys():
            valid_fields = Animal._fields.keys()
            for k, v in self.input_data['lion'].items():
                if k in valid_fields:
                    animal[k] = v
        else:
            self.response(400, 'Invalid lion data.')
            return
        if 'name' not in animal.keys():
            self.response(400, 'You must define name for the new lion.')
            return
        else:
            response = yield self.Animals.find_one({'name': animal['name']})
            if response:
                self.response(409, 'Check if you are using a name from a lion that already exists in the database.')
                return

        # Create a Imageset first
        imageset = None
        if 'imageset' in self.input_data.keys():
            if 'id' in self.input_data['imageset']:
                imageset = yield self.ImageSets.find_one({'iid': self.input_data['imageset']['id']})
                imageset['id'] = imageset['iid']

        if not imageset:
            response = yield Task(self.create_imageset, self.input_data['imageset'])
            if response and response['code'] != 200:
                self.response(response['code'], response['message'])
                return
            imageset = response['data']

        # Create a Lion now
        dt = datetime.now()
        animal['iid'] = yield Task(self.new_iid, self.animals)
        animal['created_at'] = dt
        animal['updated_at'] = dt
        animal['primary_image_set_iid'] = imageset['id']
        # # checking for required fields
        if 'organization_id' in self.input_data['lion'].keys():
            animal['organization_iid'] = self.input_data['lion']['organization_id']
            check_org = yield self.db.organizations.find_one({'iid': animal['organization_iid']})
            if not check_org:
                self.response(409, 'Invalid organization_id.')
                return
        try:
            newanimal = Animal(animal)
            newanimal.collection(self.animals)
            newanimal.validate()
            # the new object is valid, so try to save
            try:
                newsaved = yield self.Animals.insert(newanimal.to_primitive())
                output = newanimal.to_primitive()
                output['obj_id'] = str(newsaved)
                self.switch_iid(output)

                output['organization_id'] = output['organization_iid']
                del output['organization_iid']
                output['primary_image_set_id'] = output['primary_image_set_iid']
                del output['primary_image_set_iid']

                # Set Lion Id to Imageset
                try:
                    updnobj = yield self.ImageSets.update({'iid': imageset['id']}, {'$set': {'animal_iid': output['id']}})
                    # Remove the imageset from the cache to be updated
                    rem = yield Task(self.cache_remove, imageset['iid'], 'imgset')
                    info(rem)
                    self.finish(self.json_encode({
                        'status': 'success',
                        'message': 'new %s saved.' % (self.animal),
                        'data': output
                    }))
                except ValidationError as e:
                    self.response(400, "Invalid input data. Error: " + str(e) + '.')
                    return

            except Exception as e:
                # duplicated index error
                self.response(
                    409,
                    'Key violation. Check if you are using a name from a lion that already exists in the database.')
        except ValidationError as e:
            # received data is invalid in some way
            self.response(
                400,
                'Invalid input data. Errors: %s' % (str(e)))

    @asynchronous
    @coroutine
    @api_authenticated
    def put(self, animal_id=None):
        # update an animal
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(Animal)
        fields_allowed_to_be_update = ['name', 'organization_iid', 'primary_image_set_iid', 'dead']
        if 'organization_id' in self.input_data.keys():
            update_data['organization_iid'] = self.input_data['organization_id']
            del self.input_data['organization_id']
            check_org = yield self.db.organizations.find_one(
                {'iid': update_data['organization_iid']})
            if not check_org:
                self.response(409, 'Invalid organization_id.')
                return
        if 'primary_image_set_id' in self.input_data.keys():
            update_data['primary_image_set_iid'] = self.input_data['primary_image_set_id']
            del self.input_data['primary_image_set_id']
            check_imageset = yield self.ImageSets.find_one(
                {'iid': update_data['primary_image_set_iid']})
            if not check_imageset:
                self.response(409, 'Invalid primary_image_set_id.')
                return
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if animal_id and update_ok:
            query = self.query_id(animal_id)
            updobj = yield self.Animals.find_one(query)
            primimgsetid = int(updobj['primary_image_set_iid'])
            if updobj:
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        updobj[field] = update_data[field]
                updobj['updated_at'] = datetime.now()
                # Check for primery change
                if 'primary_image_set_iid' in update_data.keys():
                    newimgsetid = int(update_data['primary_image_set_iid'])
                    # Change joined images to the new primary image set
                    resp = yield self.Images.update(
                        {'$and': [{'joined': primimgsetid}, {'image_set_iid': {'$ne': newimgsetid}}]},
                        {'$set': {'joined': newimgsetid}}, multi=True)
                    # Removed joined if it is an image from the new primary image set
                    resp = yield self.Images.update(
                        {'$and': [{'joined': primimgsetid},
                                  {'image_set_iid': newimgsetid}]},
                        {'$set': {'joined': None}}, multi=True)
                    oldimgset = yield self.ImageSets.find_one({'iid': primimgsetid})
                    if oldimgset:
                        coverid = yield self.Images.find_one(
                            {'iid': oldimgset['main_image_iid']})
                        if coverid:
                            if int(coverid['image_set_iid']) != int(oldimgset['iid']):
                                resp = yield self.ImageSets.update(
                                    {'iid': oldimgset['iid']}, {'$set': {'main_image_iid': None}})
                                info(resp)
                try:
                    updid = ObjId(updobj['_id'])
                    del updobj['_id']
                    animals = Animal(updobj)
                    animals.collection(self.animals)
                    animals.validate()
                    # the object is valid, so try to save
                    try:
                        updated = yield self.Animals.update(
                            {'_id': updid}, animals.to_native())
                        info(updated)
                        output = updobj
                        output['obj_id'] = str(updid)
                        # Change iid to id in the output
                        self.switch_iid(output)
                        output['organization_id'] = output['organization_iid']
                        del output['organization_iid']
                        output['primary_image_set_id'] = output['primary_image_set_iid']
                        del output['primary_image_set_iid']
                        self.finish(self.json_encode(
                            {'status': 'success',
                             'message': self.animal + ' updated', 'data': output}))
                    except Exception as e:
                        # duplicated index error
                        self.response(409, 'Duplicated name for %s.' % (self.animal))
                except ValidationError as e:
                    # received data is invalid in some way
                    self.response(400, 'Invalid input data. Errors: %s.' % (str(e)))
            else:
                self.response(404, self.animal + ' not found.')
        else:
            self.response(
                400,
                'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, animal_id=None):
        # delete an animal
        if animal_id:
            query = self.query_id(animal_id)
            animobj = yield self.Animals.find_one(query)
            if animobj:
                rem_iid = animobj['iid']
                rem_pis = animobj['primary_image_set_iid']
                rem_pis_obj = yield self.ImageSets.find_one({'iid': rem_pis})
                if not rem_pis_obj:
                    self.response(500, 'Fail to find the object for the primary image set.')
                    return
                # 1 - Remove animal
                rmved = yield self.Animals.remove({'iid': rem_iid})
                info(str(rmved))
                # 2 - Remove its primary image set
                rmved = yield self.ImageSets.remove({'iid': rem_pis})
                # 3 - Remove images of the primary image set
                imgl = yield self.Images.find(
                    {'image_set_iid': rem_pis}).to_list(None)
                rmlist = list()
                for img in imgl:
                    # Delete the source file
                    srcurl = self.settings['S3_FOLDER'] + '/imageset_' + str(rem_pis) + '_' + str(rem_pis_obj['_id']) + '/'
                    srcurl = srcurl + img['created_at'].date().isoformat() + '_image_' + str(img['iid']) + '_' + str(img['_id'])
                    try:
                        for suf in ['_full.jpg', '_icon.jpg', '_medium.jpg', '_thumbnail.jpg']:
                            rmlist.append(srcurl + suf)
                    except Exception as e:
                        self.response(500, 'Fail to delete image in S3. Errors: %s.' % (str(e)))
                        return
                if len(rmlist) > 0:
                    rmladd = yield self.db.dellist.insert(
                        {'list': rmlist, 'ts': datetime.now()})
                    info(rmladd)
                rmved = yield self.Images.remove({'image_set_iid': rem_pis}, multi=True)
                info(str(rmved))
                # 4 - Removing association
                rmved = yield self.ImageSets.update(
                    {'animal_iid': rem_iid},
                    {'$set': {'animal_iid': None, 'updated_at': datetime.now()}}, multi=True)
                info(str(rmved))
                # 5 - Adjusting cvresults
                cursor = self.CVResults.find()
                while (yield cursor.fetch_next):
                    doc = cursor.next_object()
                    mp = loads(doc['match_probability'])
                    rmup = False
                    rmupl = list()
                    for ma in mp:
                        if int(ma['id']) == int(rem_iid):
                            rmup = True
                        else:
                            rmupl.append(ma)
                    if rmup:
                        updcvr = yield self.CVResults.update(
                            {'_id': doc['_id']}, {'$set': {'match_probability': dumps(rmupl)}})
                        info(updcvr)
            else:
                self.response(404, self.animal + ' not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')

    @asynchronous
    @engine
    def list(self, objs, orgnames, callback=None):
        """Implement the list output used for UI in the website."""
        current_user = yield self.Users.find_one({'email': self.current_user['username']})
        is_admin = current_user['admin']
        current_organization = yield self.db.organizations.find_one({'iid': current_user['organization_iid']})

        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            obj['name'] = x['name']
            obj['primary_image_set_id'] = x['primary_image_set_iid']
            if orgnames and x['organization_iid'] in orgnames.keys():
                obj['organization'] = orgnames[x['organization_iid']]
                obj['organization_id'] = x['organization_iid']
            else:
                obj['organization'] = '-'
                obj['organization_id'] = '-'
            if 'dead' in x.keys():
                obj['dead'] = x['dead']
            else:
                obj['dead'] = False
            obj['age'] = None
            obj['gender'] = None
            ivcquery = {'animal_iid': x['iid'], 'is_verified': False,
                        'iid': {"$ne": x['primary_image_set_iid']}}
            ivc = yield self.ImageSets.find(ivcquery).count()
            if ivc == 0:
                obj['is_verified'] = True
            else:
                obj['is_verified'] = False
            obj['thumbnail'] = ''
            obj['image'] = ''
            if x['primary_image_set_iid'] > 0:
                imgset = yield self.ImageSets.find_one(
                    {'iid': x['primary_image_set_iid']})
                if imgset:
                    if imgset['date_of_birth']:
                        obj['age'] = self.age(imgset['date_of_birth'])
                        obj['date_of_birth'] = imgset['date_of_birth'].date().isoformat()
                    else:
                        obj['age'] = '-'
                        obj['date_of_birth'] = '-'
                    if imgset['date_stamp']:
                        obj['date_stamp'] = imgset['date_stamp']
                    else:
                        obj['date_stamp'] = '-'
                    if imgset['tags']:
                        obj['tags'] = imgset['tags']
                    else:
                        obj['tags'] = None

                    if 'geopos_private' in imgset.keys():
                        obj['geopos_private'] = imgset['geopos_private']
                    else:
                        obj['geopos_private'] = False

                    if imgset['notes']:
                        obj['notes'] = imgset['notes']
                    else:
                        obj['notes'] = ''

                    can_show = (True if (is_admin or current_organization['iid'] == obj['organization_id']) else False) if obj['geopos_private'] else True
                    if can_show:
                        if imgset['location']:
                            obj['latitude'] = imgset['location'][0][0]
                            obj['longitude'] = imgset['location'][0][1]
                        else:
                            obj['latitude'] = None
                            obj['longitude'] = None

                        if 'tag_location' in imgset.keys():
                            obj['tag_location'] = imgset['tag_location']
                        else:
                            obj['tag_location'] = None
                    else:
                        obj['latitude'] = None
                        obj['longitude'] = None
                        obj['tag_location'] = None

                    obj['gender'] = imgset['gender']
                    # obj['is_verified'] = imgset['is_verified']
                    img = yield self.Images.find_one(
                        {'iid': imgset['main_image_iid']})
                    if img:
                        obj['thumbnail'] = self.settings['S3_URL'] + img['url'] + '_icon.jpg'
                        obj['image'] = self.settings['S3_URL'] + img['url'] + '_medium.jpg'
                    # Check algorithms
                    resp_cv = None
                    resp_wh = None
                    try:
                        resp_cv = yield self.Images.find(
                            {'image_tags': ['cv'],
                             'image_set_iid': imgset['iid']}).count()
                        resp_wh = yield self.Images.find(
                            {'$or': [
                                # {'image_tags': ['whisker']},
                                {'image_tags': ['whisker-left']},
                                {'image_tags': ['whisker-right']}],
                            'image_set_iid': imgset['iid']}).count()
                    except Exception as e:
                        info(e)
                    obj['cv'] = bool(resp_cv)
                    obj['whisker'] = bool(resp_wh)
            output.append(obj)
        callback(output)

    @asynchronous
    @engine
    def prepare_output(self, objs, noimages=False, callback=None):
        current_user = yield Task(self.get_user_by_email, self.current_user['username'])
        is_admin = current_user['admin']
        current_organization = yield self.Orgs.find_one({'iid': current_user['organization_iid']})

        objanimal = dict()
        objanimal['id'] = objs['iid']
        objanimal['name'] = objs['name']
        objanimal['organization_id'] = objs['organization_iid']
        objanimal['primary_image_set_id'] = objs['primary_image_set_iid']
        if 'dead' in objs.keys():
            objanimal['dead'] = objs['dead']
        else:
            objanimal['dead'] = False
        # Get imagesets for the animal
        imgsets = yield self.ImageSets.find(
            {'animal_iid': objanimal['id']}).to_list(None)
        imgsets_output = list()
        for oimgst in imgsets:
            obj = dict()
            obj['id'] = oimgst['iid']
            obj['is_verified'] = oimgst['is_verified']

            if 'geopos_private' in oimgst.keys():
                obj['geopos_private'] = oimgst['geopos_private']
            else:
                obj['geopos_private'] = False

            can_show = (True if (is_admin or current_organization['iid'] == objs['organization_id']) else False) if obj['geopos_private'] else True
            if can_show:
                if 'location' in oimgst.keys() and oimgst['location']:
                    obj['latitude'] = oimgst['location'][0][0]
                    obj['longitude'] = oimgst['location'][0][1]
                else:
                    obj['latitude'] = None
                    obj['longitude'] = None
                if 'tag_location' in oimgst.keys():
                    obj['tag_location'] = oimgst['tag_location']
                else:
                    obj['tag_location'] = None
            else:
                obj['latitude'] = None
                obj['longitude'] = None
                obj['tag_location'] = None

            obj['gender'] = oimgst['gender']
            if oimgst['date_of_birth']:
                obj['date_of_birth'] = oimgst['date_of_birth'].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                obj['date_of_birth'] = None
            obj['main_image_id'] = oimgst['main_image_iid']
            obj['uploading_organization_id'] = oimgst['uploading_organization_iid']
            obj['notes'] = oimgst['notes']
            obj['owner_organization_id'] = oimgst['owner_organization_iid']
            obj['user_id'] = oimgst['uploading_user_iid']
            cvreq = yield self.CVRequests.find_one(
                {'image_set_iid': oimgst['iid']})
            if cvreq:
                obj['has_cv_request'] = True
                cvres = yield self.CVResults.find_one(
                    {'cvrequest_iid': cvreq['iid']})
                if cvres:
                    obj['has_cv_result'] = True
                else:
                    obj['has_cv_result'] = False
            else:
                obj['has_cv_request'] = False
                obj['has_cv_result'] = False
            if not noimages:
                images = yield self.Images.find(
                    {'image_set_iid': oimgst['iid']}).to_list(None)
                outimages = list()
                for image in images:
                    obji = dict()
                    obji['id'] = image['iid']
                    obji['image_tags'] = image['image_tags'] if 'image_tags' in image else []
                    obji['is_public'] = image['is_public']
                    # This will be recoded
                    obji['thumbnail_url'] = ''
                    obji['main_url'] = ''
                    obji['url'] = ''
                    img = yield self.Images.find_one({'iid': image['iid']})
                    if img:
                        obji['thumbnail_url'] = self.settings['S3_URL'] + img['url'] + '_thumbnail.jpg'
                        obji['main_url'] = self.settings['S3_URL'] + img['url'] + '_full.jpg'
                        obji['url'] = self.settings['S3_URL'] + img['url'] + '_full.jpg'
                    outimages.append(obji)
                obj['_embedded'] = {'images': outimages}
            imgsets_output.append(obj)
        objanimal['_embedded'] = {'image_sets': imgsets_output}
        callback(objanimal)

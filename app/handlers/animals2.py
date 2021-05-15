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
# from models.animal import Animal
# from models.imageset import ImageSet
from datetime import datetime, time
# from bson import ObjectId as ObjId
from uuid import uuid4
from datetime import timedelta
# from pymongo import DESCENDING
from lib.rolecheck import api_authenticated
# from schematics.exceptions import ValidationError
from logging import info
# from json import loads, dumps
# from os import listdir


class AnimalsListHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET', 'POST')

    @coroutine
    @api_authenticated
    def process_list(self, token, objs, orgnames):
        try:
            info('===========================================================')
            info('initiating trello data processing: %s'
                 % datetime.now(self.utc).time())
            info('===========================================================')
            outputs = yield Task(self.list, objs, orgnames)
            # Saving New Trello data on Redis Cache
            expiresat = (
                datetime.now(self.utc) +
                timedelta(seconds=60)).strftime("%Y/%m/%d/ %H:%M:%S")
            data = {'status_code': 200,
                    'message': 'Os dados foram processados.',
                    'data': outputs,
                    'expires': expiresat}

            yield Task(self.write_token, token, data, 60)
            info('<><><><><><><><><><><><><><><><><><><><><><><><><><><>')
            info('processing ended: %s' % datetime.now(self.utc).time())
            info('<><><><><><><><><><><><><><><><><><><><><><><><><><><>')

        except Exception as e:
            expiresat = (
                datetime.now(self.utc) +
                timedelta(seconds=60)).strftime("%Y/%m/%d/ %H:%M:%S")
            data = {'status_code': 400,
                    'message': 'Falha no processamento dos dados.',
                    'data': {},
                    'expires': expiresat}
            yield Task(self.write_token, token, data, 60)
            info('<><><><><><><><><><><><><><><><><><><><><><><><><><><>')
            info('Processing error... %s', str(e))
            info('<><><><><><><><><><><><><><><><><><><><><><><><><><><>')


    @asynchronous
    @coroutine
    @api_authenticated
    def get(self):
        # Token authentication
        info(self.get_argument('token', None))
        auth = yield Task(
            self.read_token, self.get_argument('token', None))
        if not auth:
            self.response(403, 'O token informado não é válido.', {})
            return
        # try:
        message = auth['message']
        info('message %s', message)
        if auth['status_code'] == 206:
            message = (
                auth['message'] + ' Token válido até: ' + auth['expires'])
        self.response(
            auth['status_code'], message, auth['data'])
        # return
        # except Exception as e:
        #     info(str(e))
        #     self.response(400, 'Falha na execução desta operação.', {})
        #     return

    @asynchronous
    @engine
    @api_authenticated
    def post(self):
        token = yield Task(self.check_token)
        if token and token['cache']:
            cache = token['cache']
            message = cache['message']
            info(cache['message'])
            if cache['status_code'] == 206:
                info('waiting token')
                info('=======================================================')
                info('processing: %s  Token válido até:  %s'
                     % (cache['message'], cache['expires']))
                info('=======================================================')
                message = (cache['message'] + ' Token válido até: '
                           + cache['expires'])
                self.response(
                    cache['status_code'], message, cache['data'])
                return
            elif cache['status_code'] == 200:
                info('clear token')
                data = token['token']
                yield Task(self.clear_token, data)
        token = str(uuid4())
        expiration_ex = 600
        expiresat = (
            datetime.now(self.utc)
            + timedelta(seconds=expiration_ex)).strftime("%Y/%m/%d/ %H:%M:%S")
        data = {
            'status_code': 206,
            'message': 'Os dados estão sendo processados.',
            'data': {}, 'expires': expiresat}
        # try:
        if True:
            org_filter = self.get_argument('org_id', None)
            info("org_filter: %s", org_filter)
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
            if not len(objs):
                self.response(404, 'Not found.')
                return
            yield Task(self.write_token, key=token, data=data, expiration_s=expiration_ex)
            # Inserting task on APSchedule
            self.scheduler.add_job(
                AnimalsListHandler.process_list, args=(self, token, objs, orgnames), id='process_list')
            self.response(
                200,
                'Processamento Agendado. Token para obter os dados: '
                '?token=<id>.', {'token': {'id': token, 'expires': expiresat}})
        # except Exception as e:
        #     info(str(e))
        #     if token:
        #         yield Task(self.clear_token, token)
        #     self.response(400, "Falha no Processamento dos dados.")

    @asynchronous
    @engine
    def list(self, objs, orgnames, callback=None):
        """Implement the list output used for UI in the website."""
        is_admin = (self.current_user['role'] == 'admin')
        org_iid = self.current_user['org_id']

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

                    can_show = (True if (is_admin or org_iid == obj['organization_id']) else False) if obj['geopos_private'] else True
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
                        obj['thumbnail'] = self.imgurl(img['url'], 'icon') # self.settings['S3_URL'] + img['url'] + '_icon.jpg'
                        obj['image'] = self.imgurl(img['url'], 'medium') # self.settings['S3_URL'] + img['url'] + '_medium.jpg'
            # Check algorithms
            limagesets = yield self.ImageSets.find({'animal_iid': x['iid']}, {'iid': 1}).to_list(None)
            limagesets = [x['iid'] for x in limagesets]
            resp_cv = None
            resp_wh = None
            try:
                resp_cv = yield self.Images.find(
                    {'image_tags': ['cv'],
                        'image_set_iid': {'$in': limagesets}}).count()
                resp_wh = yield self.Images.find(
                    {'$or': [
                        # {'image_tags': ['whisker']},
                        {'image_tags': ['whisker-left']},
                        {'image_tags': ['whisker-right']}],
                     'image_set_iid': {'$in': limagesets}}).count()
            except Exception as e:
                info(e)
            obj['cv'] = bool(resp_cv)
            obj['whisker'] = bool(resp_wh)
            output.append(obj)
        callback(output)

    @asynchronous
    @engine
    def prepare_output(self, objs, noimages=False, callback=None):
        is_admin = (self.current_user['role'] == 'admin')
        org_iid = self.current_user['org_id']

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

            can_show = (True if (is_admin or org_iid == objs['organization_id']) else False) if obj['geopos_private'] else True
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
                        obji['thumbnail_url'] = self.imgurl(img['url'], 'thumbnail') # self.settings['S3_URL'] + img['url'] + '_thumbnail.jpg'
                        obji['main_url'] = self.imgurl(img['url'], 'full') # self.settings['S3_URL'] + img['url'] + '_full.jpg'
                        obji['url'] = self.imgurl(img['url'], 'full') # self.settings['S3_URL'] + img['url'] + '_full.jpg'
                    outimages.append(obji)
                obj['_embedded'] = {'images': outimages}
            imgsets_output.append(obj)
        objanimal['_embedded'] = {'image_sets': imgsets_output}
        callback(objanimal)

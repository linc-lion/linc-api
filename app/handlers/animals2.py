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

from handlers.base import BaseHandler
from datetime import datetime, time, timedelta
from uuid import uuid4
from lib.rolecheck import api_authenticated
from logging import info


class AnimalsListHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET', 'POST')

    @api_authenticated
    async def process_list(self, token, objs, orgnames):
        try:
            info('===========================================================')
            info('initiating trello data processing: %s'
                 % datetime.now(self.utc).time())
            info('===========================================================')
            outputs = await self.list(objs, orgnames)
            expiresat = (
                datetime.now(self.utc) +
                timedelta(seconds=60)).strftime("%Y/%m/%d/ %H:%M:%S")
            data = {'status_code': 200,
                    'message': 'Os dados foram processados.',
                    'data': outputs,
                    'expires': expiresat}

            await self.write_token(token, data, 60)
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
            await self.write_token(token, data, 60)
            info('<><><><><><><><><><><><><><><><><><><><><><><><><><><>')
            info('Processing error... %s', str(e))
            info('<><><><><><><><><><><><><><><><><><><><><><><><><><><>')

    @api_authenticated
    async def get(self):
        info(self.get_argument('token', None))
        auth = await self.read_token(self.get_argument('token', None))
        if not auth:
            self.response(403, 'O token informado não é válido.', {})
            return
        message = auth['message']
        info('message %s', message)
        if auth['status_code'] == 206:
            message = auth['message'] + ' Token válido até: ' + auth['expires']
        self.response(auth['status_code'], message, auth['data'])

    @api_authenticated
    async def post(self):
        token = await self.check_token()
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
                await self.clear_token(data)
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
            objs = await self.Animals.find(query_ani).to_list(None)
            orgs = await self.db.organizations.find(query_org).to_list(None)
            orgnames = dict()
            for org in orgs:
                orgnames[org['iid']] = org['name']
            if not len(objs):
                self.response(404, 'Not found.')
                return
            await self.write_token(key=token, data=data, expiration_s=expiration_ex)
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
        #         await self.clear_token(token)
        #     self.response(400, "Falha no Processamento dos dados.")

    @api_authenticated
    async def list(self, objs, orgnames, callback=None):
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
            ivc = await self.ImageSets.find(ivcquery).count()
            if ivc == 0:
                obj['is_verified'] = True
            else:
                obj['is_verified'] = False
            obj['thumbnail'] = ''
            obj['image'] = ''
            if x['primary_image_set_iid'] > 0:
                imgset = await self.ImageSets.find_one(
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
                    img = await self.Images.find_one(
                        {'iid': imgset['main_image_iid']})
                    if img:
                        obj['thumbnail'] = self.imgurl(img['url'], 'icon')
                        obj['image'] = self.imgurl(img['url'], 'medium')
            limagesets = await self.ImageSets.find({'animal_iid': x['iid']}, {'iid': 1}).to_list(None)
            limagesets = [x['iid'] for x in limagesets]
            resp_cv = None
            resp_wh = None
            try:
                resp_cv = await self.Images.find(
                    {'image_tags': ['cv'],
                     'image_set_iid': {'$in': limagesets}}).count()
                resp_wh = await self.Images.find(
                    {'$or': [
                        {'image_tags': ['whisker-left']},
                        {'image_tags': ['whisker-right']}],
                     'image_set_iid': {'$in': limagesets}}).count()
            except Exception as e:
                info(e)
            obj['cv'] = bool(resp_cv)
            obj['whisker'] = bool(resp_wh)
            output.append(obj)
        callback(output)

    @api_authenticated
    async def prepare_output(self, objs, noimages=False, callback=None):
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
        imgsets = await self.ImageSets.find(
            {'animal_iid': objanimal['id']}).to_list(None)
        imgsets_output = list()
        for oimgst in imgsets:
            obj = dict()
            obj['id'] = oimg

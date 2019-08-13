#!/usr/bin/env python3
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

from logging import info
from datetime import datetime
from tornado.gen import coroutine
from json import dumps
from time import time
import zipfile
from os import listdir, remove
from secrets import token_urlsafe

@coroutine
def dbdump(db, url_preffix, file_path):
    ini = time()
    info('================================')
    info('== Starting DB Dump ==')
    info('================================')
    for filen in listdir(file_path):
        if filen.startswith('lion-db-dump-'):
            info('Removing file: {}'.format(file_path + filen))
            remove(file_path + filen)
    filename = 'lion-db-dump-' + datetime.utcnow().isoformat()
    filename = filename.replace(':', '-').split('.')[0] + '-' + token_urlsafe(48)
    info('Creating file: {}'.format(file_path + filename + '.zip'))
    # Get all Imagesets associated with a lion
    imgsets = list(db.imagesets.find({}, {'animal_iid': 1}))
    iids = [x['animal_iid'] for x in imgsets if x['animal_iid']]
    # Get the unique ids of the imagesets associated
    iids = list(set(iids))
    # Get the lions from the ids gathered
    objs = list(db.lions.find({'iid': {'$in': iids}}))
    # Prepare dataset
    output = list()
    for x in objs:
        objanimal = dict()
        if 'dead' not in x.keys():
            objanimal['dead'] = False
        else:
            objanimal['dead'] = x['dead']
        objanimal['id'] = x['iid']
        objanimal['name'] = x['name']
        objanimal['organization_id'] = x['organization_iid']
        objanimal['primary_image_set_id'] = x['primary_image_set_iid']
        # Get imagesets for the animal
        imgsets = list(db.imagesets.find(
            {'animal_iid': x['iid']}))
        imgsets_output = list()
        for oimgst in imgsets:
            obj = dict()
            obj['id'] = oimgst['iid']
            obj['is_verified'] = oimgst['is_verified']
            if 'geopos_private' in oimgst.keys():
                obj['geopos_private'] = oimgst['geopos_private']
            else:
                obj['geopos_private'] = False
            # can_show = (True if (is_admin or current_organization['iid'] == objs['organization_id']) else False) if obj['geopos_private'] else True
            # if can_show:
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
            cvreq = db.cvrequests.find_one(
                {'image_set_iid': oimgst['iid']})
            if cvreq:
                obj['has_cv_request'] = True
                cvres = db.cvresults.find_one(
                    {'cvrequest_iid': cvreq['iid']})
                if cvres:
                    obj['has_cv_result'] = True
                else:
                    obj['has_cv_result'] = False
            else:
                obj['has_cv_request'] = False
                obj['has_cv_result'] = False

            images = list(db.images.find(
                {'image_set_iid': oimgst['iid']}))
            outimages = list()
            for image in images:
                obji = dict()
                obji['id'] = image['iid']
                obji['image_tags'] = image['image_tags'] if 'image_tags' in image else []
                obji['is_public'] = image['is_public']
                obji['url'] = self.imgurl(image['url'], 'full')
                outimages.append(obji)
            obj['_embedded'] = {'images': outimages}
            imgsets_output.append(obj)
        objanimal['_embedded'] = {'image_sets': imgsets_output}
        output.append(objanimal)
    exec_time = time() - ini
    data = {'data': output, 'dump_execution_time_in_seconds': exec_time}
    with open(file_path + filename + '.json', 'w+') as f:
        f.write(dumps(data))
        f.close()
    with zipfile.ZipFile(file_path + filename + '.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_path + filename + '.json',
                   filename.split('/')[-1] + '.json')
        zipf.close()
        remove(file_path + filename + '.json')
    info('================================')
    info('== DB Dump finished ==')
    info('================================')

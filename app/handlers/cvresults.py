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
from tornado.gen import engine, coroutine
from handlers.base import BaseHandler
from bson import ObjectId as ObjId
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.escape import json_decode
from json import loads
from lib.rolecheck import api_authenticated
from logging import info


class CVResultsHandler(BaseHandler):
    """A class that handles requests about CV identificaiton results informartion
    """

    def query_id(self, res_id):
        """This method configures the query that will find an object"""
        try:
            query = {'iid': int(res_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(res_id)}
            except Exception as e:
                self.response(400, 'Invalid id key.')
                return
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, res_id=None, xlist=None):
        if res_id:
            if res_id == 'list':
                objs = yield self.CVResults.find().to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status': 'success', 'data': self.list(objs)}))
            else:
                query = self.query_id(res_id)
                obj_cvr = yield self.CVResults.find_one(query)
                if obj_cvr:
                    if not xlist:
                        objres = dict(obj_cvr)
                        self.switch_iid(objres)
                        objres['obj_id'] = str(obj_cvr['_id'])
                        del objres['_id']
                        output = objres
                    else:
                        # List data following the website form
                        obj_cvq = yield self.CVRequests.find_one({'iid': obj_cvr['cvrequest_iid']})

                        req_body = loads(obj_cvq['request_body'])
                        for k, v in req_body.items():
                            info('{} = {}'.format(k, v))
                        obj_cvr['results'] = loads(obj_cvr['match_probability'])
                        del obj_cvr['match_probability']
                        info(obj_cvr)

                        # output = {'cvq': obj_cvq, 'cvr': obj_cvr}

                        output = {'results': list()}
                        output['lions_found'] = req_body['lions_found']
                        output['lions_submitted'] = req_body['lions_submitted']
                        output['classifiers'] = req_body['classifiers']

                        output['results']

                        # mp = loads(objs['match_probability'])

                        for i in obj_cvr['results']:
                            objres = dict()
                            # objres['id'] = int(i['id'])
                            objres['id'] = 9
                            objres['primary_image_set_id'] = ''
                            objres['name'] = '-'
                            objres['thumbnail'] = ''
                            objres['image'] = ''
                            objres['age'] = '-'
                            objres['gender'] = ''
                            objres['tags'] = '[]'
                            objres['is_verified'] = False
                            objres['organization'] = ''
                            objres['organization_id'] = ''
                            # get the animal
                            aobj = yield self.Animals.find_one({'iid': objres['id']})
                            if aobj:
                                objres['name'] = aobj['name']
                                objres['primary_image_set_id'] = aobj['primary_image_set_iid']
                                img = yield self.Images.find_one(
                                    {'image_set_iid': aobj['primary_image_set_iid'],
                                     'image_tags': 'main-id'})
                                if img:
                                    objres['thumbnail'] = self.settings['S3_URL'] + img['url'] + '_icon.jpg'
                                    objres['image'] = self.settings['S3_URL'] + img['url'] + '_medium.jpg'
                                else:
                                    img = yield self.Images.find(
                                        {'image_set_iid': aobj['primary_image_set_iid']}).to_list(length=1)
                                    if len(img) > 0:
                                        objres['thumbnail'] = self.settings['S3_URL'] + img[0]['url'] + '_icon.jpg'
                                        objres['image'] = self.settings['S3_URL'] + img[0]['url'] + '_medium.jpg'
                                    else:
                                        objres['thumbnail'] = ''
                                        objres['image'] = ''
                                imgss = yield self.ImageSets.find_one({'iid': aobj['primary_image_set_iid']})
                                if imgss:
                                    objres['age'] = self.age(imgss['date_of_birth'])
                                    objres['gender'] = imgss['gender']
                                    objres['tags'] = imgss['tags']
                                    objres['is_verified'] = imgss['is_verified']
                                if aobj:
                                    objres['organization_id'] = aobj['organization_iid']
                                    org = yield self.db.organizations.find_one({'iid': aobj['organization_iid']})
                                    if org:
                                        objres['organization'] = org['name']

                            # objres['cv'] = i['confidence']
                            objres['cv'] = 7.827403010196576e-07
                            objres['whisker'] = 1.1841663763334509e-05
                            objres['prediction'] = 0.75
                            output['results'].append(objres)
                            break
                        assoc = {'id': None, 'name': None}
                        reqstatus = '-'
                        if obj_cvq:
                            reqid = obj_cvq['iid']
                            reqstatus = obj_cvq['status']
                            imgset = yield self.ImageSets.find_one({'iid': obj_cvq['image_set_iid']})
                            if imgset:
                                assoc['id'] = imgset['animal_iid']
                                if imgset['animal_iid']:
                                    lname = yield self.Animals.find_one({'iid': imgset['animal_iid']})
                                    if lname:
                                        assoc['name'] = lname['name']
                        output = {'table': output, 'associated': assoc, 'status': reqstatus, 'req_id': reqid}
                    #
                    self.response(200, 'CV results data.', output)
                    # self.set_status(200)
                    # self.finish(self.json_encode({'status': 'success', 'data': output}))
                else:
                    # self.set_status(404)
                    # self.finish(self.json_encode({'status': 'error', 'message': 'not found'}))
                    self.response(404, 'CV results not found.')
        else:
            objs = yield self.CVResults.find().to_list(None)
            output = list()
            for x in objs:
                obj = dict(x)
                obj['obj_id'] = str(x['_id'])
                del obj['_id']
                obj['cvrequest_id'] = obj['cvrequest_iid']
                del obj['cvrequest_iid']
                self.switch_iid(obj)
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status': 'success', 'data': output}))

    @api_authenticated
    def post(self):
        self.response(400, "CV Results objects are created automatically, you can't POST to create them.")

    @api_authenticated
    def put(self, res_id=None):
        self.response(400, "CV Results objects are updated automatically, you can't PUT to update them.")

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, res_id=None):
        # delete an res
        if res_id:
            query = self.query_id(res_id)
            updobj = yield self.CVResults.find_one(query)
            if updobj:
                # removing cvrequest and cvresult related and they will be added in
                # a history collection
                try:
                    idcvres = ObjId(updobj['_id'])
                    del updobj['_id']
                    newhres = yield self.db.cvresults_history.insert(updobj)
                    info(newhres)
                    cvres = yield self.CVResults.remove({'_id': idcvres})
                    info(cvres)
                    self.response(200, 'CVresult successfully deleted.')
                except Exception as e:
                    self.response(500, 'Fail to delete cvresult.')
            else:
                self.response(404, 'CVresult not found.')
        else:
            self.response(400, 'Remove requests (DELETE) must have a resource ID.')

    def list(self, objs):
        """ Implements the list output used for UI in the website
        """
        output = list()
        for x in objs:
            obj = dict(x)
            self.switch_iid(obj)
            obj['obj_id'] = str(obj['_id'])
            del obj['_id']
            output.append(obj)
        return output

    @asynchronous
    @engine
    def checkresult(self, jobid, callback=None):
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        http_client = AsyncHTTPClient()
        url = self.settings['CVSERVER_URL_RESULTS']
        request = HTTPRequest(**{
            'url': url + jobid,
            'method': 'GET',
            'auth_username': self.settings['CV_USERNAME'],
            'auth_password': self.settings['CV_PASSWORD'],
            'request_timeout': 720
        })
        try:
            response = yield http_client.fetch(request)
            rbody = json_decode(response.body)
            rbody['code'] = response.code
            rbody['reason'] = response.reason
        except Exception as e:
            rbody = {}
        callback(rbody)

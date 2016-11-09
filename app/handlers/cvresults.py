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
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.cv import CVResult
from bson import ObjectId as ObjId
from datetime import datetime
from tornado.httpclient import AsyncHTTPClient,HTTPRequest,HTTPError
from tornado.escape import json_decode
from json import dumps,loads
from lib.rolecheck import allowedRole, refusedRole, api_authenticated
from schematics.exceptions import ValidationError

class CVResultsHandler(BaseHandler):
    """A class that handles requests about CV identificaiton results informartion
    """

    def query_id(self,res_id):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(res_id) }
        except:
            try:
                query = { '_id' : ObjId(res_id) }
            except:
                self.response(400,'Invalid id key.')
                return
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, res_id=None, xlist=None):
        if res_id:
            if res_id == 'list':
                objs = yield self.settings['db'].cvresults.find().to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs)}))
            else:
                query = self.query_id(res_id)
                objs = yield self.settings['db'].cvresults.find_one(query)
                if objs:
                    if not xlist:
                        objres = dict(objs)
                        self.switch_iid(objres)
                        objres['obj_id'] = str(objs['_id'])
                        del objres['_id']
                        output = objres
                    else:
                        # List data following the website form
                        animl = yield self.settings['db'][self.settings['animals']].find().to_list(None)
                        animl = [x['iid'] for x in animl]
                        output = list()
                        mp = loads(objs['match_probability'])
                        for i in mp:
                            # Prevent search a deleted lion
                            if int(i['id']) not in animl:
                                continue
                            objres = dict()
                            objres['id'] = int(i['id'])
                            objres['name'] = '-'
                            objres['thumbnail'] = ''
                            objres['image'] = ''
                            objres['age'] = '-'
                            objres['gender'] = ''
                            objres['is_verified'] = False
                            objres['organization'] = ''
                            objres['organization_id'] = ''
                            # get the animal
                            aobj = yield self.settings['db'][self.settings['animals']].find_one({'iid':objres['id']})
                            if aobj:
                                #cvreq = yield self.settings['db'].cvrequests.find_one({'iid':objs['cvrequest_iid']})
                                # here
                                img = yield self.settings['db'].images.find_one({'image_set_iid':aobj['primary_image_set_iid'],'image_type':'main-id'})
                                if img:
                                    objres['thumbnail'] = self.settings['S3_URL']+img['url']+'_icon.jpg'
                                    objres['image'] = self.settings['S3_URL']+img['url']+'_medium.jpg'
                                else:
                                    img = yield self.settings['db'].images.find({'image_set_iid':aobj['primary_image_set_iid']}).to_list(length=1)
                                    if len(img) > 0:
                                        objres['thumbnail'] = self.settings['S3_URL']+img[0]['url']+'_icon.jpg'
                                        objres['image'] = self.settings['S3_URL']+img[0]['url']+'_medium.jpg'
                                    else:
                                        objres['thumbnail'] = ''
                                        objres['image'] = ''

                                if aobj:
                                    objres['name'] = aobj['name']
                                imgss = yield self.settings['db'].imagesets.find_one({'iid':aobj['primary_image_set_iid']})
                                if imgss:
                                    objres['age'] = self.age(imgss['date_of_birth'])
                                    objres['gender'] = imgss['gender']
                                    objres['is_verified'] = imgss['is_verified']
                                if aobj:
                                    objres['organization_id'] = aobj['organization_iid']
                                    org = yield self.settings['db'].organizations.find_one({'iid':aobj['organization_iid']})
                                    if org:
                                        objres['organization'] = org['name']

                            objres['cv'] = i['confidence']
                            output.append(objres)
                        cvreq = yield self.settings['db'].cvrequests.find_one({'iid':objs['cvrequest_iid']})
                        assoc = {'id': None,'name':None }
                        reqstatus = '-'
                        if cvreq:
                            reqid = cvreq['iid']
                            reqstatus = cvreq['status']
                            imgset = yield self.settings['db'].imagesets.find_one({'iid':cvreq['image_set_iid']})
                            if imgset:
                                assoc['id'] = imgset['animal_iid']
                                if imgset['animal_iid']:
                                    lname = yield self.settings['db'][self.settings['animals']].find_one({'iid':imgset['animal_iid']})
                                    if lname:
                                        assoc['name'] = lname['name']
                        output = {'table':output,'associated':assoc,'status':reqstatus,'req_id':reqid}
                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':output}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            objs = yield self.settings['db'].cvresults.find().to_list(None)
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
            self.finish(self.json_encode({'status':'success','data':output}))

    @api_authenticated
    def post(self):
        self.response(400,"CV Results objects are created automatically, you can't POST to create them.")

    @api_authenticated
    def put(self, res_id=None):
        self.response(400,"CV Results objects are updated automatically, you can't PUT to update them.")

    @asynchronous
    @coroutine
    @api_authenticated
    def delete(self, res_id=None):
        # delete an res
        if res_id:
            query = self.query_id(res_id)
            updobj = yield self.settings['db'].cvresults.find_one(query)
            if updobj:
                # removing cvrequest and cvresult related and they will be added in
                # a history collection
                try:
                    idcvres = ObjId(updobj['_id'])
                    del updobj['_id']
                    newhres = yield self.settings['db'].cvresults_history.insert(updobj)
                    cvres = yield self.settings['db'].cvresults.remove({'_id':idcvres})
                    self.response(200,'CVresult successfully deleted.')
                except:
                    self.response(500,'Fail to delete cvresult.')
            else:
                self.response(404,'CVresult not found.')
        else:
            self.response(400,'Remove requests (DELETE) must have a resource ID.')

    def list(self,objs):
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
    def checkresult(self,jobid,callback=None):
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        http_client = AsyncHTTPClient()
        url = self.settings['CVSERVER_URL_RESULTS']
        request = HTTPRequest(**{
            'url' : url+jobid,
            'method' : 'GET',
            'auth_username' : self.settings['CV_USERNAME'],
            'auth_password' : self.settings['CV_PASSWORD'],
            'request_timeout': 720
        })
        try:
            response = yield http_client.fetch(request)
            rbody = json_decode(response.body)
            rbody['code'] = response.code
            rbody['reason'] = response.reason
        except:
            rbody = {}
        callback(rbody)

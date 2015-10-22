#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import coroutine,Task
from handlers.base import BaseHandler
from models.organization import Organization
from models.animal import Animal
from models.imageset import ImageSet,Image
from models.cv import CVRequest,CVResult

from tornado.httpclient import AsyncHTTPClient,HTTPRequest
from json import dumps

class ImageSetsHandler(BaseHandler):
    """A class that handles requests about image sets informartion
    """
    @asynchronous
    @coroutine
    def get(self, imageset_id=None, cvrequest=False):
        if imageset_id:
            if imageset_id == 'list':
                # Show a list for the website
                # Get imagesets from the DB
                objs_imgsets = yield ImageSet.objects.find_all()
                #objs_imgsets = [x.to_son() for x in objs_imgsets]
                # Initialize animals class
                Animals = Animal()
                Animals.set_collection(self.settings['animals'])
                output = list()

                for obj in objs_imgsets:
                    imgset_obj = dict()
                    imgset_obj['obj_id'] = str(obj._id)
                    imgset_obj['id'] = obj.iid


                    if obj.animal_iid:
                        obja = yield Animals.objects.filter(iid=obj.animal_iid).find_all()
                        imgset_obj['name'] = obja[0].name
                    else:
                        imgset_obj['name'] = '-'

                    obji = yield Image.objects.filter(image_set_iid=obj.iid,image_type='main-id').find_all()
                    if len(obji) > 0:
                        url = obji[0].url[:obji[0].url.index('.com/')+5]
                        imgset_obj['thumbnail'] = url + obji[0].thumbnail_image_uid
                    else:
                        obji = yield Image.objects.filter(image_set_iid=obj.iid).find_all()
                        if len(obji) > 0:
                            url = obji[0].url[:obji[0].url.index('.com/')+5]
                            imgset_obj['thumbnail'] = url + obji[0].thumbnail_image_uid
                        else:
                            imgset_obj['thumbnail'] = ''

                    if obj.date_of_birth:
                        imgset_obj['age'] = self.age(born=obj.date_of_birth)
                    else:
                        imgset_obj['age'] = '-'

                    if obj.owner_organization_iid:
                        objo = yield Organization.objects.filter(iid=obj.owner_organization_iid).find_all()
                        imgset_obj['organization'] = objo[0].name
                    else:
                        imgset_obj['organization'] = '-'

                    imgset_obj['gender'] = obj.gender
                    imgset_obj['is_verified'] = obj.is_verified
                    imgset_obj['is_primary'] = obj.is_primary

                    objcvreq = yield CVRequest.objects.filter(image_set_iid=obj.iid).find_all()
                    if len(objcvreq) > 0:
                        imgset_obj['cvrequest'] = str(objcvreq[0]._id)
                    else:
                        imgset_obj['cvrequest'] = None

                    imgset_obj['cvresults'] = None
                    if len(objcvreq) > 0:
                        objcvres = yield CVResult.objects.filter(cv_request_iid=objcvreq[0].iid).find_all()
                        if len(objcvres) > 0:
                            imgset_obj['cvresults'] = str(objcvres[0]._id)
                    output.append(imgset_obj)
                self.finish(self.json_encode({'status':'success','data':output}))
            elif cvrequest:
                # Send a request for identification in the CV Server
                body = {
                  "identification": {
                    "images": [
                      {"id": 123, "type": "whisker", "url": "https://s3.amazonaws.com/semanticmd-api-testing/api/cbc90b5705d51e9e218b0a7e518aa6d3506c190c"}
                      ],
                    "gender": "m",
                    "age": 5,
                    "lions": [
                      {"id": 456, "url": "http://lg-api.com/lions/456", "updated_at": "timestamp"}
                    ]
                  }
                }

                http_client = AsyncHTTPClient()
                url = self.settings['CVSERVER_URL_IDENTIFICATION']
                request = HTTPRequest(**{
                    'url' : self.settings['CVSERVER_URL_IDENTIFICATION'],
                    'method' : 'POST',
                    'auth_username' : self.settings['CV_USERNAME'],
                    'auth_password' : self.settings['CV_PASSWORD'],
                    'body' : dumps(body)
                })
                response = yield http_client.fetch(request)

                self.set_status(response.code)
                self.finish({'message':response.reason})
            else:
                # return a specific imageset
                self.finish({'message':'work in progress'})
        else:
            # return a list of imagesets
            objs = yield ImageSet.objects.find_all()
            objs = [x.to_son() for x in objs]
            self.finish(self.json_encode(objs))

    def put(self, imageset_id):
        # update an imageset
        pass

    def post(self):
        # create a new imageset
        pass

    def delete(self, item_id):
        # delete an imageset
        pass


class ImagesHandler(BaseHandler):
    """A class that handles requests about images
    """
    @asynchronous
    @coroutine
    def get(self):
        objs = yield Image.objects.find_all()
        objs = [x.to_son() for x in objs]
        self.finish(self.json_encode(objs))

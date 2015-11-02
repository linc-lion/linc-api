#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.cv import CVResult
from bson import ObjectId as ObjId
from datetime import datetime
from tornado.httpclient import AsyncHTTPClient,HTTPRequest,HTTPError

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
                self.dropError(400,'invalid id key')
                return
        return query

    @asynchronous
    @coroutine
    def get(self, res_id=None):
        if res_id:
            if res_id == 'list':
                objs = yield self.settings['db'].cvresults.find().to_list(None)
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs)}))
            else:
                query = self.query_id(res_id)
                print(query)
                objs = yield self.settings['db'].cvresults.find_one(query)
                if objs:
                    objres = objs[0].to_son()
                    objres['id'] = objs[0].iid
                    objres['obj_id'] = str(objs[0]._id)
                    del objres['iid']

                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':objres}))
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
                self.switch_iid(obj)
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status':'success','data':output}))

    @asynchronous
    @engine
    def post(self):
        """ This method only creates a cvresult if still doesn't exist """
        # create a new res
        # parse data recept by POST and get only fields of the object
        if not 'cvrequest_id' in self.input_data.keys():
            self.dropError(400,'you must provide a cvrequest_id')
            return
        else:
            if cvrequest_id == 'all':
                # create cvresults for all cvrequest that still doesn't have one
                pass
            else:
                cvrequest_id = self.input_data['cvrequest_id']
                # check the cvrequest
                cvreq = yield self.settings['db'].cvrequests.find_one({'iid':cvrequest_id})
                if not cvreq:
                    self.dropError(404,'cvrequest_id provided not found')
                    return
                # check if exists
                cvres = yield self.settings['db'].cvresults.find_one({'cvrequest_iid':cvrequest_id})
                if cvres:
                    # exists, so tray to update if the status is uncompleted
                    self.setSuccess(400,'a result for the cvrequest_id '+cvrequest_id+' already exists and the cvrequest has status = '+cvreq['status']+'. To update it send a PUT request in the /cvresults')
                    return
                else:
                    # create a cvresult
                    newobj = dict()
                    newobj['iid'] = yield Task(self.new_iid,CVResult.__collection__)
                    newobj['cvrequest_iid'] = cvrequest_id
                    dt = datetime.now()
                    newobj['created_at'] = dt
                    newobj['updated_at'] = dt
                    # Check the result in the Server
                    results = yield Task(self.checkresult,cvreq['server_uuid'])
                    newobj['match_probability'] = '[]'
                    rcode_to_cvrequest = 'fail'
                    if results:
                        if results['code'] == 200:
                            newobj['match_probability'] = dumps(results['identification']['lions'])
                            rcode_to_cvrequest = results['identification']['status']
                    """
                    CV Server status responses: "queued", "processing", "finished", and "error".
                    API have: "fail" that means the communication with cv server fail
                    """
                    # save the new cvresult in the database
                    try:
                        newres = CVResult(**newobj)
                        if newres.validate():
                            try:
                                # updating the cvrequest with the status
                                cvrequ = self.settings['db'].cvrequests.update({'_id':cvreq['_id']},{'$set':{'status':rcode_to_cvrequest,'updated_at':datetime.now()}})
                                newsaved = yield newres.save()
                                output = newsaved.to_son()
                                output['obj_id'] = str(newsaved._id)
                                self.switch_iid(output)
                                output['cvrequest_id'] = output['cvrequest_iid']
                                del output['cvrequest_iid']
                                self.finish(self.json_encode({'status':'success','message':'new cv results saved','data':output}))
                            except:
                                # duplicated index error
                                self.dropError(409,'an error check for indexing violation. the cv results was not created.')
                    except:
                        # received data is invalid in some way
                        self.dropError(500,'fail to save the new cvresult')

    @asynchronous
    @coroutine
    def put(self, res_id=None):
        """ This method implements the update for a cvresult that already exists """
        # update an res
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(CVResult)
        fields_allowed_to_be_update = ['match_probability']
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in update_data.keys():
                update_ok = True
                break
        if res_id and update_ok:
            query = self.query_id(res_id)
            updobj = yield self.settings['db'].cvresults.find_one(query)

            if updobj:
                updobj = updobj[0]
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        cmd = "updobj."+field+" = "
                        if isinstance(update_data[field],str):
                            cmd = cmd + "'" + str(update_data[field]) + "'"
                        else:
                            cmd = cmd + str(update_data[field])
                        exec(cmd)
                updobj.updated_at = datetime.now()
                try:
                    if updobj.validate():
                        # the object is valid, so try to save
                        try:
                            saved = yield updobj.save()
                            output = saved.to_son()
                            output['obj_id'] = str(saved._id)
                            # Change iid to id in the output
                            self.switch_iid(output)
                            output['image_set_id'] = output['image_set_iid']
                            del output['image_set_iid']
                            self.finish(self.json_encode({'status':'success','message':'image updated','data':output}))
                        except:
                            # duplicated index error
                            self.dropError(409,'key violation')
                except:
                    # received data is invalid in some way
                    self.dropError(400,'Invalid input data.')
            else:
                self.dropError(404,'cv result not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    def delete(self, res_id=None):
        # delete an res
        if res_id:
            query = self.query_id(res_id)
            updobj = yield self.settings['db'].cvresults.find_one(query)
            if updobj:
                # removing cvrequest and cvresult related and they will be added in
                # a history collection
                #try:
                if True:
                    idcvres = ObjId(str(updobj))
                    del updobj['_id']
                    newhres = yield self.settings['db'].cvresults_history.insert(updobj)
                    cvres = yield self.settings['db'].cvresults.remove({'_id':idcvres})
                    self.setSuccess(200,'cvresult successfully deleted')
                #except:
                else:
                    self.dropError(500,'fail to delete cvresult')
            else:
                self.dropError(404,'cvresult not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    def list(self,objs):
        """ Implements the list output used for UI in the website
        """
        output = list()
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            output.append(obj)
        return output

    @asynchronous
    @engine
    def checkresult(self,jobid,callback=None):
        http_client = AsyncHTTPClient()
        url = self.settings['CVSERVER_URL_RESULTS']
        request = HTTPRequest(**{
            'url' : url+jobid,
            'method' : 'GET',
            'auth_username' : self.settings['CV_USERNAME'],
            'auth_password' : self.settings['CV_PASSWORD'],
            'body' : dumps(body)
        })
        try:
            response = yield http_client.fetch(request)
            rbody = json_decode(response.body)
            rbody['code'] = response.code
            rbody['reason'] = responde.reason
        except:
            rbody = {}
        callback(rbody)

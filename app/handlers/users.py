#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import asynchronous
from tornado.gen import engine,coroutine,Task
from handlers.base import BaseHandler
from models.user import User
from bson import ObjectId as ObjId
from datetime import datetime
from schematics.exceptions import ValidationError
from lib.rolecheck import allowedRole, refusedRole, api_authenticated
from logging import info

class UsersHandler(BaseHandler):
    """A class that handles requests about users informartion
    """

    def query_id(self,user_id,trashed=False):
        """This method configures the query that will find an object"""
        try:
            query = { 'iid' : int(user_id) }
        except:
            try:
                query = { '_id' : ObjId(user_id) }
            except:
                query = { 'email' : user_id}
        query['trashed'] = trashed
        return query

    @asynchronous
    @coroutine
    @api_authenticated
    def get(self, user_id=None):
        trashed = self.get_argument('trashed',False)
        if trashed:
            if trashed == '*':
                trashed = { '$in' : [True,False] }
            else:
                trashed = (trashed.lower() == 'true')
        if user_id:
            if user_id == 'list':
                objs = yield self.settings['db'].users.find({'trashed':trashed}).to_list(None)
                orgs = yield self.settings['db'].organizations.find({'trashed':trashed}).to_list(None)
                orgnames = dict()
                for org in orgs:
                    orgnames[org['iid']] = org['name']
                for obj in objs:
                    del obj['encrypted_password']
                self.set_status(200)
                self.finish(self.json_encode({'status':'success','data':self.list(objs,orgnames)}))
            elif user_id == 'conservationists':
                orgs = yield self.settings['db'].organizations.find({'trashed':False}).to_list(None)
                users = yield self.settings['db'].users.find({'trashed':False}).to_list(None)
                orglist = dict()
                for org in orgs:
                    if org['name'] not in orglist.keys():
                        orglist[org['name']] = list()
                    for user in users:
                        if user['organization_iid'] == org['iid']:
                            orglist[org['name']].append(user['email'])
                rm = list()
                for k,v in orglist.iteritems():
                    if len(v) == 0:
                        rm.append(k)
                for k in rm:
                    del orglist[k]
                self.setSuccess(200,'Ok, works',orglist)
            else:
                # return a specific user accepting as id the integer id, hash and name
                query = self.query_id(user_id,trashed)
                objs = yield self.settings['db'].users.find_one(query)
                #yield User.objects.filter(**query).limit(1).find_all()
                if objs:
                    objuser = objs
                    objuser['obj_id'] = str(objs['_id'])
                    self.switch_iid(objuser)
                    del objuser['_id']
                    objuser['organization_id'] = objuser['organization_iid']
                    del objuser['organization_iid']
                    del objuser['encrypted_password']

                    self.set_status(200)
                    self.finish(self.json_encode({'status':'success','data':objuser}))
                else:
                    self.set_status(404)
                    self.finish(self.json_encode({'status':'error','message':'not found'}))
        else:
            # return a list of users
            #objs = yield User.objects.find_all()
            objs = yield self.settings['db'].users.find({'trashed':trashed}).to_list(None)
            output = list()
            for x in objs:
                obj = dict(x)
                obj['obj_id'] = str(x['_id'])
                del obj['_id']
                del obj['encrypted_password']
                obj['organization_id'] = obj['organization_iid']
                del obj['organization_iid']
                self.switch_iid(obj)
                output.append(obj)
            self.set_status(200)
            self.finish(self.json_encode({'status':'success','data':output}))

    @asynchronous
    @engine
    @api_authenticated
    @allowedRole('admin')
    def post(self):
        # create a new user
        # parse data recept by POST and get only fields of the object
        newobj = self.parseInput(User)
        # getting new integer id
        newobj['iid'] = yield Task(self.new_iid,User.collection())
        # encrypt password
        newobj['encrypted_password'] = self.encryptPassword(self.input_data['password'].encode('utf-8'))
        orgiid = self.input_data['organization_id']
        orgexists = yield self.settings['db'].organizations.find_one({'iid':orgiid,'trashed':False})
        if orgexists:
            newobj['organization_iid'] = orgiid
        else:
            self.dropError(409,"organization referenced doesn't exist")
            return
        try:
            newuser = User(newobj)
            newuser.validate()
            # the new object is valid, so try to save
            try:
                newsaved = yield self.settings['db'].users.insert(newuser.to_native())
                output = newuser.to_native()
                output['obj_id'] = str(newsaved)
                output['organization_id'] = output['organization_iid']
                del output['organization_iid']
                self.switch_iid(output)
                del output['encrypted_password']
                self.finish(self.json_encode({'status':'success','message':'new user saved','data':output}))
            except:
                # duplicated index error
                self.dropError(409,'key violation')
        except ValidationError, e:
            # received data is invalid in some way
            self.dropError(400,'Invalid input data. Errors: '+str(e))

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def put(self, user_id=None):
        # update an user
        # parse data recept by PUT and get only fields of the object
        update_data = self.parseInput(User)
        fields_allowed_to_be_update = ['email','trashed','organization_iid','admin','password']
        if 'organization_id' in self.input_data.keys():
            orgiid = self.input_data['organization_id']
            orgexists = yield self.settings['db'].organizations.find_one({'iid':orgiid,'trashed':False})
            if orgexists:
                update_data['organization_iid'] = orgiid
            else:
                self.dropError(409,"organization referenced doesn't exist")
                return
        # validate the input for update
        update_ok = False
        for k in fields_allowed_to_be_update:
            if k in self.input_data.keys():
                update_ok = True
                break
        if user_id and update_ok:
            query = self.query_id(user_id)
            if 'trashed' in update_data.keys():
                del query['trashed']
            updobj = yield self.settings['db'].users.find_one(query)
            #User.objects.filter(**query).limit(1).find_all()
            if updobj:
                for field in fields_allowed_to_be_update:
                    if field in update_data.keys():
                        updobj[field] = update_data[field]
                if 'password' in self.input_data.keys():
                    updobj['encrypted_password'] = self.encryptPassword(self.input_data['password'])
                updobj['updated_at'] = datetime.now()
                updid = ObjId(updobj['_id'])
                del updobj['_id']
                try:
                    updobj = User(updobj)
                    updobj.validate()
                    # the object is valid, so try to save
                    try:
                        updobj = updobj.to_native()
                        updobj['_id'] = updid
                        saved = yield self.settings['db'].users.update({'_id':updid},updobj)
                        output = updobj
                        output['obj_id'] = str(updid)
                        del output['_id']
                        # Change iid to id in the output
                        self.switch_iid(output)
                        del output['encrypted_password']
                        output['organization_id'] = output['organization_iid']
                        del output['organization_iid']
                        self.finish(self.json_encode({'status':'success','message':'user updated','data':output}))
                    except:
                        # duplicated index error
                        self.dropError(409,'invalid data for update')
                except ValidationError, e:
                    # received data is invalid in some way
                    self.dropError(400,'Invalid input data. Errors: '+str(e))
            else:
                self.dropError(404,'user not found')
        else:
            self.dropError(400,'Update requests (PUT) must have a resource ID and update pairs for key and value.')

    @asynchronous
    @coroutine
    @api_authenticated
    @allowedRole('admin')
    def delete(self, user_id=None):
        # delete an user
        if user_id:
            query = self.query_id(user_id)
            updobj = yield self.settings['db'].users.find_one(query)
            if updobj:
                # check for references
                refcount = 0
                iid = updobj['iid']
                # imageset - uploading_user_iid
                imgsetrc = yield self.settings['db'].imagesets.find({'uploading_user_iid':iid,'trashed':False}).count()
                info('Checking references in imagesets:' + str(imgsetrc))
                refcount += imgsetrc
                if refcount > 0:
                    self.dropError(417,"the user can't be deleted because it has references in the database.")
                else:
                    try:
                        updobj = yield self.settings['db'].users.update(query,{'$set':{'trashed':True,'updated_at':datetime.now()}})
                        self.setSuccess(200,'user successfully deleted')
                    except:
                        self.dropError(500,'fail to delete user')
            else:
                self.dropError(404,'user not found')
        else:
            self.dropError(400,'Remove requests (DELETE) must have a resource ID.')

    def list(self,objs,orgnames=None):
        """ Implements the list output used for UI in the website
        """
        output = list()
        print(orgnames)
        for x in objs:
            obj = dict()
            obj['id'] = x['iid']
            obj['email'] = x['email']
            if orgnames and x['organization_iid'] in orgnames.keys():
                obj['organization'] = orgnames[x['organization_iid']]
            else:
                obj['organization'] = '-'
            output.append(obj)
        return output

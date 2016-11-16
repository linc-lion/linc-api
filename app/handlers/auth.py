#!/usr/bin/env python
# coding: utf-8

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
from tornado.gen import coroutine,Task
from handlers.base import BaseHandler
from datetime import datetime,timedelta
from lib.tokens import gen_token,token_encode,token_decode
from lib.rolecheck import api_authenticated
from tornado.escape import utf8
from tornado import web
from json import dumps
from logging import info
from bson import ObjectId as ObjId
from schematics.exceptions import ValidationError
from models.user import User
from tornado.httpclient import AsyncHTTPClient

class CheckAuthHandler(BaseHandler):
    @api_authenticated
    def get(self):
        x_real_ip = self.request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or self.request.remote_ip
        output = {
            'login ip':self.current_user['ip'],
            'check ip':remote_ip,
        }
        self.response(200,'Token valid and the user '+self.current_user['username']+' is still logged.',output)

class LoginHandler(BaseHandler):
    @asynchronous
    @coroutine
    def post(self):
        if 'username' in self.input_data.keys() and \
           'password' in self.input_data.keys():
            username = self.input_data['username']
            password = self.input_data['password']
            wlist = self.settings['wait_list']
            count = self.settings['attempts']
            ouser = yield self.settings['db'].users.find_one({'email':username})
            if username in wlist.keys():
                dt = wlist[username]
                if datetime.now() < dt + timedelta(minutes=30):
                    self.response(401,'Authentication failed, your user have more than 3 attempts so you must wait 30 minutes since your last attempt.')
                    return
                else:
                    del wlist[username]
            if ouser:
                if self.checkPassword(utf8(password),utf8(ouser['encrypted_password'])):
                    # Ok: password matches
                    x_real_ip = self.request.headers.get("X-Real-IP")
                    remote_ip = x_real_ip or self.request.remote_ip
                    if ouser['admin']:
                        role = 'admin'
                    else:
                        role = 'user'
                    org = yield self.settings['db'].organizations.find_one({'iid':ouser['organization_iid']})
                    orgname = ''
                    if org:
                         orgname = org['name']
                    token = gen_token(24)
                    objuser = { 'id': ouser['iid'],
                                'username':ouser['email'],
                                'orgname':orgname,
                                'org_id':ouser['organization_iid'],
                                'role': role,
                                'token': token,
                                'ip':remote_ip,
                                'timestamp':datetime.now().isoformat()}
                    # update user info about the login
                    datupd = {'$set':{'updated_at':datetime.now(),
                                      'sign_in_count':int(ouser['sign_in_count'])+1,
                                      'last_sign_in_ip':ouser['current_sign_in_ip'],
                                      'last_sign_in_at':ouser['current_sign_in_at'],
                                      'current_sign_in_at':datetime.now(),
                                      'current_sign_in_ip':remote_ip
                                      }
                             }
                    upduser = self.settings['db'].users.update({'iid':ouser['iid']},datupd)
                    authtoken = web.create_signed_value(self.settings['cookie_secret'],'authtoken',dumps(objuser))
                    if username in wlist.keys():
                        del wlist[username]
                    if username in count.keys():
                        del count[username]
                    self.settings['tokens'][username] = { 'token' : token, 'dt' : datetime.now() }
                    # Encode to output
                    outputtoken = token_encode(authtoken,self.settings['token_secret'])
                    # Output Response
                    outputdata = {'token':outputtoken,
                                  'role':role,'orgname':orgname,
                                  'id': ouser['iid'],
                                  'organization_id': ouser['organization_iid']}
                    self.response(200,'Authentication OK.',outputdata,{'Linc-Api-AuthToken':outputtoken})
                    return
                else:
                    # wrong password
                    if username in count.keys() and datetime.now() < count[username]['d'] + timedelta(minutes=30):
                        count[username]['c'] += 1
                    else:
                        count[username] = {'c' : 1, 'd' : None}
                    count[username]['d'] = datetime.now()
                    if count[username]['c'] > 3:
                        wlist[username] = datetime.now()
                        self.response(401,'Authentication failure, and you have more than three attempts in 30 minutes, so you will need to wait 30 minutes to try to login again.')
                    else:
                        self.response(401,'Authentication failure, password incorrect.')
            else:
                self.response(401,'Authentication failure. Username or password are incorrect or maybe the user are disabled.')
        else:
            self.response(400,'Authentication requires username and password')

class LogoutHandler(BaseHandler):
    @api_authenticated
    def post(self):
        info(self.settings['attempts'])
        info(self.settings['tokens'])
        info(self.settings['wait_list'])
        if self.current_user['username'] in self.settings['tokens'].keys():
            del self.settings['tokens'][self.current_user['username']]
            self.response(200,'Logout OK.')
        else:
            self.response(400,'Authentication token invalid. User already logged off.')

class RestorePassword(BaseHandler):
    @asynchronous
    @coroutine
    def post(self):
        if 'email' in self.input_data.keys():
            email = self.input_data['email']
            ouser = yield self.settings['db'].users.find_one({'email':email})
            if ouser:
                newpass = gen_token(10)
                encpass = self.encryptPassword(newpass)
                ouser['encrypted_password'] = encpass
                ouser['updated_at'] = datetime.now()
                updid = ObjId(ouser['_id'])
                del ouser['_id']
                try:
                    updobj = User(ouser)
                    updobj.validate()
                    info(updobj)
                    # the object is valid, so try to save
                    try:
                        updobj = updobj.to_native()
                        updobj['_id'] = updid
                        saved = yield self.settings['db'].users.update({'_id':updid},updobj)
                        emails = [email]
                        admin_emails = yield self.settings['db'].users.find({'admin':True}).to_list(None)
                        for i in admin_emails:
                            emails.append(i['email'])
                        emails = list(set(emails))
                        # DEPLOY = This will be removed
                        info(emails)
                        emails = [email]
                        # DEPLOY = end
                        # -- Send email
                        pemail = False
                        for email_address in emails:
                            emailmsg = dict()
                            emailmsg['html'] = 'A password recovery was requested for the email '+email+'.<br>\nYou can use the credentials:<br>\nUsername: '+email+'<br>\nPassword: '+newpass+'<br><br>\n\nto log-in the system https://linc.linclion.org/ <br><br>\n\nLinc Lion Team\n<br>'

                            emailmsg['text'] = 'A password recovery was requested for the email '+email+'.\nYou can use the credentials:\nUsername: '+email+'\nPassword: '+newpass+'\n\nto log-in the system in https://linc.linclion.org/ \n\nLinc Lion Team\n'

                            emailmsg['subject'] = "LINC Lion: Password recovery"
                            emailmsg['from_email'] = "suporte@venidera.net"
                            emailmsg['from_name'] = "LINC Lion"
                            emailmsg['to'] = [{"email": email_address,"name": email_address}]

                            http_client = AsyncHTTPClient()
                            mail_url = 'http://labs.venidera.com:12800/messages/send.json'
                            mail_data = {
                                "key": 'dyNJmiW2RPxZoKqi1u-bXw',
                                "message": emailmsg,
                                "exception": True
                            }
                            body = self.json_encode(mail_data)
                            response = yield Task(http_client.fetch, mail_url, method='POST', body=body)
                            if 200 <= response.code < 300:
                                if email == email_address:
                                    pemail = True
                        if pemail:
                            self.response(200,'A new password was sent to the user.')
                        else:
                            self.response(400,'The system can\'t generate a new password for the user. Ask for support in suporte@venidera.com')
                        return
                    except:
                        self.response(400,'Fail to generate new password.')
                except ValidationError as e:
                    # received data is invalid in some way
                    self.response(400,'Invalid input data. Errors: '+str(e)+'.')
            else:
                self.response(404,'No user found with email: '+email)
        else:
            self.response(400,'An email is required to restart user\'s passwords.')

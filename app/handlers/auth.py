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
from tornado.gen import coroutine, Task
from handlers.base import BaseHandler
from datetime import datetime, timedelta
from lib.tokens import gen_token, token_encode
from lib.rolecheck import api_authenticated
from tornado.escape import utf8
from tornado import web
from json import dumps
from logging import info


class CheckAuthHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET')

    @api_authenticated
    def get(self):
        x_real_ip = self.request.headers.get("X-Real-IP")
        remote_ip = x_real_ip or self.request.remote_ip
        output = {
            'login ip': self.current_user['ip'],
            'check ip': remote_ip,
        }
        self.response(200,
                      'Token valid and the user ' + self.current_user['username'] + ' is still logged.',
                      output)


class LoginHandler(BaseHandler):
    SUPPORTED_METHODS = ('POST')

    @asynchronous
    @coroutine
    def post(self):
        if 'username' in self.input_data.keys() and \
           'password' in self.input_data.keys():
            username = self.input_data['username']
            password = self.input_data['password']
            wlist = self.settings['wait_list']
            count = self.settings['attempts']
            ouser = yield Task(self.get_user_by_email, username)
            if username in wlist.keys():
                dt = wlist[username]
                if datetime.now() < dt + timedelta(minutes=30):
                    self.response(401,
                                  'Authentication failed, your user have more than 3 attempts so you must wait 30 minutes since your last attempt.')
                    return
                else:
                    del wlist[username]
            if ouser:
                if self.checkPassword(utf8(password), utf8(ouser['encrypted_password'])):
                    # Ok: password matches
                    x_real_ip = self.request.headers.get("X-Real-IP")
                    remote_ip = x_real_ip or self.request.remote_ip
                    if ouser['admin']:
                        role = 'admin'
                    else:
                        role = 'user'
                    org = yield Task(self.get_org_by_id, ouser['organization_iid'])
                    orgname = ''
                    if org:
                        orgname = org['name']
                    token = gen_token(24)
                    objuser = {
                        'id': ouser['iid'],
                        'username': ouser['email'],
                        'orgname': orgname,
                        'org_id': ouser['organization_iid'],
                        'role': role,
                        'token': token,
                        'ip': remote_ip,
                        'timestamp': datetime.now().isoformat()}
                    # update user info about the login
                    datupd = {'$set': {
                        'updated_at': datetime.now(),
                        'sign_in_count': int(ouser['sign_in_count']) + 1,
                        'last_sign_in_ip': ouser['current_sign_in_ip'],
                        'last_sign_in_at': ouser['current_sign_in_at'],
                        'current_sign_in_at': datetime.now(),
                        'current_sign_in_ip': remote_ip
                    }}
                    upduser = yield self.Users.update({'iid': ouser['iid']}, datupd)
                    # update({'iid': ouser['iid']}, datupd)
                    info(upduser)
                    authtoken = web.create_signed_value(
                        self.settings['cookie_secret'], 'authtoken', dumps(objuser))
                    if username in wlist.keys():
                        del wlist[username]
                    if username in count.keys():
                        del count[username]
                    self.settings['tokens'][username] = {'token': token, 'dt': datetime.now()}
                    # Encode to output
                    outputtoken = token_encode(authtoken, self.settings['token_secret'])
                    # Output Response
                    outputdata = {'token': outputtoken,
                                  'role': role, 'orgname': orgname,
                                  'id': ouser['iid'],
                                  'organization_id': ouser['organization_iid']}
                    self.response(200, 'Authentication OK.', outputdata, {'Linc-Api-AuthToken': outputtoken})
                    return
                else:
                    # wrong password
                    if username in count.keys() and datetime.now() < count[username]['d'] + timedelta(minutes=30):
                        count[username]['c'] += 1
                    else:
                        count[username] = {'c': 1, 'd': None}
                    count[username]['d'] = datetime.now()
                    if count[username]['c'] > 3:
                        wlist[username] = datetime.now()
                        self.response(
                            401,
                            'Authentication failure, and you have more than three attempts in 30 minutes, so you will need to wait 30 minutes to try to login again.')
                    else:
                        self.response(
                            401,
                            'Authentication failure, password incorrect.')
            else:
                self.response(401, 'Authentication failure. Username or password are incorrect or maybe the user are disabled.')
        else:
            self.response(400, 'Authentication requires username and password')


class LogoutHandler(BaseHandler):
    SUPPORTED_METHODS = ('POST')

    @api_authenticated
    def post(self):
        info(self.settings['attempts'])
        info(self.settings['tokens'])
        info(self.settings['wait_list'])
        if self.current_user['username'] in self.settings['tokens'].keys():
            del self.settings['tokens'][self.current_user['username']]
            self.response(200, 'Logout OK.')
        else:
            self.response(400, 'Authentication token invalid. User already logged off.')


class ChangePasswordHandler(BaseHandler):
    SUPPORTED_METHODS = ('POST')

    @asynchronous
    @coroutine
    @api_authenticated
    def post(self):
        if 'new_password' in self.input_data.keys():
            if len(self.input_data['new_password']) >= 6:
                resp = self.db
                ouser = yield Task(self.get_user_by_email, self.current_user['username'])
                if ouser:
                    resp = yield Task(self.changePassword, ouser, self.input_data['new_password'])
                    self.response(resp[0], resp[1])
                else:
                    self.response(400, 'Invalid user requesting password change.')
            else:
                self.response(400, 'Password must have at least 6 characters.')
        else:
            self.response(400, 'To change your password, you must send it in a json object with the key \'new_password\'.')


class RestorePassword(BaseHandler):
    SUPPORTED_METHODS = ('POST')

    @asynchronous
    @coroutine
    def post(self):
        if 'email' in self.input_data.keys():
            email = self.input_data['email']
            ouser = yield self.Users.find_one({'email': email})
            if ouser:
                try:
                    newpass = gen_token(10)
                    resp = yield Task(self.changePassword, ouser, newpass)
                    if resp[0] != 200:
                        self.response(resp[0], resp[1])
                        return
                    emails = [email]
                    admin_emails = yield self.Users.find({'admin': True}).to_list(None)
                    for i in admin_emails:
                        emails.append(i['email'])
                    emails = list(set(emails))
                    pemail = False
                    for emailaddress in emails:
                        msg = """From: %s\nTo: %s\nSubject: LINC Lion: Password recovery\n

A password recovery was requested for the email %s.\nYou can use the credentials:\n\nUsername: %s\nPassword: %s\n\nto log-in the system in https://linc.linclion.org/ \n\nLinc Lion Team\n

                        """
                        msg = msg % (self.settings['EMAIL_FROM'], emailaddress, email, email, newpass)
                        pemail = yield Task(self.sendEmail, emailaddress, msg)
                    if pemail:
                        self.response(200, 'A new password was sent to the user.')
                    else:
                        self.response(400, 'The system can\'t generate a new password for the user. Ask for support in suporte@venidera.com')
                    return
                except Exception as e:
                    self.response(400, 'Fail to generate new password.')
            else:
                self.response(404, 'No user found with email: %s' % (email))
        else:
            self.response(400, 'An email is required to restart user\'s passwords.')


class RequestAccessHandler(BaseHandler):
    SUPPORTED_METHODS = ("POST")

    @asynchronous
    @coroutine
    def post(self):
        if 'email' in self.input_data.keys():
            msg = """From: %s\nTo: %s\nSubject: LINC Lion: Request New Access to Linc\n

A new user is requesting access to Linc.\nThe user data is:\nemail: %s\nFull Name: %s\nOrganization: %s\nGeographical Study Area: %s\n\nLinc Lion Team\n

                """
            msg = msg % (
                self.settings['EMAIL_FROM'],
                self.settings['EMAIL_NEWUSER'],
                self.input_data['email'],
                self.input_data['fullname'],
                self.input_data['organization'],
                self.input_data['geographical'])
            pemail = yield Task(self.sendEmail, self.settings['EMAIL_NEWUSER'], msg)
            if pemail:
                self.response(200, 'A new access request email was sent to %s.' % (self.settings['EMAIL_NEWUSER']))
            else:
                self.response(400, 'The system can not send the access request. Ask for support in info@lionguardians.org')
        else:
            self.response(400, 'An email is required to request access')

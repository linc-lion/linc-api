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
from dateutil.relativedelta import relativedelta
from lib.tokens import gen_token, token_encode, token_decode
from lib.rolecheck import api_authenticated
from tornado.escape import utf8
from tornado import web
from json import loads, dumps
from logging import info
from uuid import uuid4
from urllib.parse import quote, unquote
from logging import info
from models.agreement import Agreement


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

                    agree = yield self.Agreements.find_one({'user_iid': ouser['iid']})
                    dp = datetime.now() - relativedelta(months=6)
                    # if agree:
                    # info('agree date: %s = %s days ago', agree['agree_date'], (datetime.now() - agree['agree_date']).days)
                    if not agree or (agree and agree['agree_date'] < dp):
                        user_id = str(ouser['_id'])
                        hashkey = str(uuid4())
                        authtoken = dumps({
                            'email': username,
                            'token': gen_token(6),
                            'key': hashkey
                        })
                        dtime = 300
                        self.cache.set('agreement:' + user_id, authtoken, dtime)
                        code = token_encode(authtoken, self.settings['token_secret'][:10])
                        self.response(
                            412,
                            'The user must accept the EULA conditions. '
                            'In order to do that, you must login in the '
                            'LINC website and accept the terms. '
                            'Note that this acceptance expires after 6 months.',
                            {'agree_code': code})
                        return

                    # Ok: password matches and user has agreement
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


class AgreementHandler(BaseHandler):
    SUPPORTED_METHODS = ('POST', 'DELETE')

    @asynchronous
    @coroutine
    def post(self):
        if 'agree_code' in self.input_data.keys():
            agree_code = self.input_data['agree_code']
            detoken = loads(token_decode(agree_code, self.settings['token_secret'][:10]))

            ouser = yield Task(self.get_user_by_email, detoken['email'])
            if ouser:
                user_id = str(ouser['_id'])
                obj = loads(self.cache.get('agreement:' + user_id))
                if obj['email'] == detoken['email'] and obj['token'] == detoken['token'] and \
                    obj['key'] == detoken['key']:
                    dtnow = datetime.now()

                    # Ok: token match
                    agree = yield self.Agreements.find_one({'user_iid': ouser['iid']})
                    if not agree:
                        info('not agree')
                        agree_data = {
                            'user_iid': ouser['iid'],
                            'organization_iid': ouser['organization_iid'],
                            'agree_date': dtnow,
                            'created_at': dtnow,
                            'updated_at': dtnow
                        }
                        try:
                            newagree = Agreement(agree_data)
                            newagree.validate()
                            yield self.Agreements.insert(newagree.to_native())
                        except Exception as e:
                            # agree register exist - continue
                            info(e)
                    else:
                        info('agree : %s', agree)
                        try:
                            query = {'$set':{'agree_date': dtnow, 'updated_at': dtnow}}
                            info(query)
                            yield self.Agreements.update({'_id': agree['_id']}, query)
                        except Exception as e:
                            info(e)

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
                    authtoken = web.create_signed_value(
                        self.settings['cookie_secret'], 'authtoken', dumps(objuser))

                    self.settings['tokens'][ouser['email']] = {'token': token, 'dt': datetime.now()}
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
                    # wrong agreement token
                    self.response( 401, 'Authentication failure, user did not accept the contract (EULA).')
            else:
                self.response(401, 'Authentication failure. Username or token are incorrect or maybe the user are disabled.')
        else:
            self.response(400, 'Authentication requires token')

    @coroutine
    @api_authenticated
    def delete(self, user_id=None):
        # delete a agree by id
        if user_id:
            updobj = yield self.Agreements.find_one({'user_iid': int(user_id)})
            if updobj:
                try:
                    rmstatus = yield self.Agreements.remove({'_id': updobj['_id']})
                    info('agree removed %s', rmstatus)
                    self.response(200, 'Agreement successfully removed.')
                except Exception as e:
                    self.response(500, 'Fail to remove agreement.')
            else:
                self.response(404, 'Agreement not found.')
        else:
            self.response(400, 'Remove agreement (DELETE) must have a resource ID.')


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


class RecoveryPassword(BaseHandler):
    SUPPORTED_METHODS = ("POST")

    # @asynchronous
    # @coroutine
    # def get(self, code=None):
    #     if code:
    #         response = {
    #             'title': 'Invalid Request',
    #             'message': 'Authentication key is invalid.'
    #         }
    #         try:
    #             token = token_decode(code, self.settings['token_secret'][:10])
    #             if token:
    #                 detoken = loads(token)
    #                 lkeys = self.settings['cache'].keys()
    #                 keys = list()
    #                 for k in lkeys:
    #                     if b'update_password:' in k:
    #                         keys.append(k)

    #                 for i in keys:
    #                     obj = loads(self.settings['cache'].get(i))
    #                     if obj['email'] == detoken['email'] and obj['password'] == detoken['password'] and\
    #                             obj['token'] == detoken['token'] and obj['key'] == detoken['key']:
    #                         ouser = yield self.Users.find_one({'email': detoken['email']})
    #                         user_id = str(ouser['_id'])
    #                         if ouser:
    #                             try:
    #                                 resp = yield Task(self.changePassword, ouser, obj['password'])
    #                                 if resp:
    #                                     self.settings['cache'].delete('update_password:' + user_id)
    #                                     response['title'] = 'Change Password!'
    #                                     response['message'] = 'The password was updated successfully.'
    #                                     self.response(200, response['message'], response)
    #                                 else:
    #                                     self.response(400, 'Unable to change password.')
    #                             except Exception as e:
    #                                 self.response(400, 'Unable to change password. ' + str(e))
    #                         else:
    #                             self.response(400, 'Unable to change password. User not found')
    #                         return
    #                 self.response(400, 'Failed to change password.')
    #             else:
    #                 self.response(400, 'This code is invalid or expired.')
    #         except Exception as e:
    #             info(e)
    #             self.response(400, 'This code is invalid or expired.')
    #     else:
    #         self.response(400, 'An code is required to use this resource.')

    @asynchronous
    @coroutine
    def post(self, code=None):
        if code:
            if 'password' in self.input_data.keys() and len(self.input_data['password']) >= 8:
                response = {
                    'title': 'Invalid Request',
                    'message': 'Authentication key is invalid.'
                }
                try:
                    token = token_decode(code, self.settings['token_secret'][:10])
                    if token:
                        detoken = loads(token)
                        lkeys = self.settings['cache'].keys()
                        keys = list()
                        for k in lkeys:
                            if b'update_password:' in k:
                                keys.append(k)

                        for i in keys:
                            obj = loads(self.settings['cache'].get(i))
                            if obj['email'] == detoken['email'] and\
                                    obj['token'] == detoken['token'] and obj['key'] == detoken['key']:
                                ouser = yield self.Users.find_one({'email': detoken['email']})
                                user_id = str(ouser['_id'])
                                if ouser:
                                    try:
                                        resp = yield Task(self.changePassword, ouser, self.input_data['password'])
                                        if resp:
                                            self.settings['cache'].delete('update_password:' + user_id)
                                            response['title'] = 'Change Password!'
                                            response['message'] = 'The password was updated successfully.'
                                            self.response(200, response['message'], response)
                                        else:
                                            self.response(400, 'Unable to change password.')
                                    except Exception as e:
                                        self.response(400, 'Unable to change password. ' + str(e))
                                else:
                                    self.response(400, 'Unable to change password. User not found')
                                return
                        self.response(400, 'Failed to change password.')
                    else:
                        self.response(400, 'This code is invalid or expired.')
                except Exception as e:
                    info(e)
                    self.response(400, 'This code is invalid or expired.')
            else:
                self.response(400, 'This code is invalid or expired.')
        elif 'email' in self.input_data.keys():
            email = self.input_data['email']
            # password = self.input_data['password']
            ouser = yield self.Users.find_one({'email': email})
            if ouser:
                try:
                    user_id = str(ouser['_id'])
                    remote_ip = self.request.headers.get("X-Real-IP") or self.request.remote_ip

                    hashkey = str(uuid4())
                    key = 'update_password:' + user_id
                    data = {'email': email,
                            'token': gen_token(6), 'key': hashkey}
                    utoken = dumps(data, default=str)
                    dtime = 300
                    self.settings['cache'].set(name=key, value=utoken, ex=dtime)

                    vdate = (datetime.now() + timedelta(seconds=dtime)).strftime("%Y/%m/%d")
                    vtime = (datetime.now() + timedelta(seconds=dtime)).strftime("%H:%M:%S")
                    code = token_encode(utoken, self.settings['token_secret'][:10])
                    code = quote(code, safe='')
                    ulink = self.settings['APP_URL'] + '/#!/auth/recovery/' + code

                    fromaddr = self.settings['EMAIL_FROM']
                    toaddr = ouser['email']

                    message_subject = 'LINC Lion: Password recovery'
                    message_text = """
                        From the IP Address: %s \n
                        A password recovery was requested for the email %s.\n
                        If you have requested and want to change the password use the link: %s \n
                        If you did not request or do not want to update your password, please disregard this email.\n
                        Link is valid for %s minutes \n
                        Valid until: %s at %s hours.\n\n
                        Linc Lion Team\n
                    """
                    message_text = message_text % (remote_ip, ouser['email'], ulink, int(dtime / 60), vdate, vtime)

                    message = "From: %s\r\n" % fromaddr + "To: %s\r\n" % toaddr + "Subject: %s\r\n" % message_subject + "\r\n" + message_text
                    message = message.encode('utf-8')
                    toaddrs = [toaddr]

                    pemail = yield Task(self.sendEmail, toaddrs, message)

                    if pemail:
                        self.response(200, 'A new password was sent to the user.')
                    else:
                        self.response(400, 'The system can\'t generate a new password for the user. Ask for support in suporte@venidera.com')
                    return
                except Exception as e:
                    info(e)
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

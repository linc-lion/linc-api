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

from tornado.web import RequestHandler, asynchronous
from tornado.gen import engine
from tornado import web
import string
from datetime import date, datetime
from logging import info
import bcrypt
from json import loads, dumps
from lib.tokens import token_decode
from lib.rolecheck import api_authenticated
from os import remove
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from tornado.httputil import HTTPHeaders
from bson import ObjectId as ObjId
from schematics.exceptions import ValidationError
from models.user import User
import smtplib
import csv


class BaseHandler(RequestHandler):
    """A class to collect common handler methods - all other handlers should
    inherit this one.
    """

    def initialize(self):
        self.animal = self.settings['animal']
        self.animals = self.settings['animals']

    def prepare(self):
        # self.auth_check()
        self.input_data = dict()
        if self.request.method in ['POST', 'PUT'] and \
           "Content-Type" in self.request.headers.keys() and \
           self.request.headers["Content-Type"].startswith("application/json"):
            try:
                if self.request.body:
                    self.input_data = loads(self.request.body.decode("utf-8"))
                for k, v in self.request.arguments.items():
                    if str(k) != str(self.request.body.decode("utf-8")):
                        self.input_data[k] = v[0].decode("utf-8")
            except ValueError:
                self.response(400, 'Fail to parse input data.')

    def get_current_user(self):
        max_days_valid = 365
        # check for https comunication
        using_ssl = (self.request.headers.get('X-Scheme', 'http') == 'https')
        if not using_ssl:
            info('Not using SSL')
        else:
            info('Using SSL')
        # get the token for authentication
        token = self.request.headers.get("Linc-Api-AuthToken")
        res = None
        if token:
            # Decode to test
            try:
                token = token_decode(token, self.settings['token_secret'])
                vtoken = web.decode_signed_value(self.settings["cookie_secret"], 'authtoken', token, max_age_days=max_days_valid)
            except Exception as e:
                vtoken = None
            if vtoken:
                dtoken = loads(vtoken.decode('utf-8'))
                if dtoken['username'] in self.settings['tokens'].keys() and \
                   self.settings['tokens'][dtoken['username']]['token'] == dtoken['token']:
                    res = dtoken
            else:
                # Validation error
                self.token_passed_but_invalid = True
        return res

    @asynchronous
    @engine
    def new_iid(self, collection, callback=None):
        iid = yield self.settings['db'].counters.find_and_modify(
            query={'_id': collection},
            update={'$inc': {'next': 1}},
            new=True, upsert=True)
        callback(int(iid['next']))

    def query_id(self, req_id):
        """ This method configures the query to find an object """
        query = None
        try:
            query = {'iid': int(req_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(req_id)}
            except Exception as e:
                query = {'name': str(req_id)}
        return query

    def parseInput(self, objmodel):
        valid_fields = objmodel._fields.keys()
        newobj = dict()
        for k, v in self.input_data.items():
            if k in valid_fields:
                newobj[k] = v
        return newobj

    def switch_iid(self, obj):
        obj['id'] = obj['iid']
        del obj['iid']

    def response(self, code, message="", data=None, headers=None):
        output_response = {'status': None, 'message': message}
        if data:
            output_response['data'] = data
        if code < 300:
            output_response['status'] = 'success'
        elif code >= 300 and code < 400:
            output_response['status'] = 'redirect'
        elif code >= 400 and code < 500:
            output_response['status'] = 'error'
        else:
            output_response['status'] = 'fail'
        if headers and isinstance(headers, dict):
            for k, v in headers.items():
                self.add_header(k, v)
        self.set_status(code)
        self.write(self.json_encode(output_response))
        self.finish()

    def json_encode(self, value):
        return dumps(value, default=str).replace("</", "<\\/")

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

    def age(self, born):
        if born:
            today = date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        else:
            return "-"

    def encryptPassword(self, password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def checkPassword(self, password, hashed):
        return bcrypt.hashpw(password, hashed) == hashed

    def imgurl(self, urlpath, imgtype='thumbnail'):
        # type can be: full,medium,thumbnail and icon
        url = self.settings['S3_URL'] + urlpath
        if imgtype == 'thumbnail':
            url = url + '_thumbnail.jpg'
        elif imgtype == 'full':
            url = url + '_full.jpg'
        elif imgtype == 'icon':
            url = url + '_icon.jpg'
        else:
            # imgtype == 'medium':
            url = url + '_medium.jpg'
        return url

    def remove_file(self, fname):
        try:
            remove(fname)
        except Exception as e:
            pass

    def sanitizestr(self, strs):
        txt = "%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c for c in strs if c in txt)

    @asynchronous
    @engine
    def api(self, url, method, body=None, headers=None, auth_username=None, auth_password=None, callback=None):
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        http_client = AsyncHTTPClient()
        dictheaders = {"content-type": "application/json"}
        if headers:
            for k, v in headers.items():
                dictheaders[k] = v
        h = HTTPHeaders(dictheaders)
        params = {
            'headers': h,
            'url': url,
            'method': method,
            'request_timeout': 720,
            'validate_cert': False}
        if method in ['POST', 'PUT']:
            params['body'] = body
        if auth_username:
            params['auth_username'] = auth_username
            params['auth_password'] = auth_password
        request = HTTPRequest(**params)
        try:
            response = yield http_client.fetch(request)
        except HTTPError as e:
            info('HTTTP error returned... ')
            info("Code: " + str(e.code))
            info("Message: " + str(e.log_message))
            if e.response:
                info('URL: ' + str(e.response.effective_url))
                info('Reason: ' + str(e.response.reason))
                info('Body: ' + str(e.response.body))
                response = e.response
            else:
                response = e
        except Exception as e:
            # Other errors are possible, such as IOError.
            info("Other Errors: " + str(e))
            response = e
        callback(response)

    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            self.response(status_code, 'Resource not found. Check the URL.')
        elif status_code == 405:
            self.response(status_code, 'This request is not allowed in this resource. Check your verb (GET,POST,PUT and DELETE)')
        else:
            self.response(status_code, 'Request results is an error with the code: %d' % (status_code))

    @asynchronous
    @engine
    def changePassword(self, ouser, newpass, callback=None):
        encpass = self.encryptPassword(newpass)
        ouser['encrypted_password'] = encpass
        ouser['updated_at'] = datetime.now()
        updid = ObjId(ouser['_id'])
        del ouser['_id']
        try:
            updobj = User(ouser)
            updobj.validate()
            # the object is valid, so try to save
            try:
                updobj = updobj.to_native()
                updobj['_id'] = updid
                saved = yield self.settings['db'].users.update({'_id': updid}, updobj)
                info(saved)
                resp = [200, 'Password changed successfully.']
            except Exception as e:
                resp = [400, 'Fail to update password.']
        except ValidationError as e:
            resp = [400, 'Invalid input data. Errors: ' + str(e) + '.']
        callback(resp)

    @asynchronous
    @engine
    def sendEmail(self, toaddr, msg, callback):
        resp = True
        try:
            fromaddr = self.settings['EMAIL_FROM']
            smtp_server = self.settings['SMTP_SERVER']
            smtp_username = self.settings['SMTP_USERNAME']
            smtp_password = self.settings['SMTP_PASSWORD']
            smtp_port = self.settings['SMPT_PORT']
            server = smtplib.SMTP(host=smtp_server,
                                  port=smtp_port,
                                  timeout=10)
            server.set_debuglevel(10)
            server.starttls()
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.sendmail(fromaddr, toaddr, msg)
            server.quit()
        except Exception as e:
            resp = False
        callback(resp)


class VersionHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET')

    def get(self):
        self.response(200, self.settings['version'] + ' - animal defined: ' + self.animal)


class DocHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET')

    def get(self):
        self.set_header('Content-Type', 'text/html; charset=UTF-8')
        self.render('documentation.html')


class DataExportHandler(BaseHandler):
    SUPPORTED_METHODS = ('POST')

    def check_structure(self, key, data):
        if key in data:
            if isinstance(data, list):
                if all([True if isinstance(x, int) else False for x in data]):
                    return True
        return False

    def write_csv(self, cursor):
        fn = str(ObjId()) + '.csv'
        with open(fn, 'w', newline='') as csvfile:
            # Sample
            fieldnames = ['first_name', 'last_name']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({'first_name': 'Baked', 'last_name': 'Beans'})
            writer.writerow({'first_name': 'Lovely', 'last_name': 'Spam'})
            writer.writerow(
                {'first_name': 'Wonderful', 'last_name': 'Spam'})
        return fn

    @api_authenticated
    def post(self):
        if self.check_structure('lions', self.input_data):
            # Query mongodb
            self.response(200, 'Will return a file to download.')
        elif self.check_structure('imagesets', self.input_data):
            # Query mongodb
            self.response(200, 'Will return a file to download.')
        else:
            self.response(400, 'Invalid call.')

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
from datetime import date
from logging import info
import bcrypt
from json import loads, dumps
from lib.tokens import token_decode
from os import remove
from lib.db import DBMethods
from lib.http import HTTPMethods
import smtplib
from tornado.web import HTTPError


class BaseHandler(RequestHandler, DBMethods, HTTPMethods):
    # A class to collect common handler methods - all other handlers should inherit this one.

    def initialize(self):
        # Strings configured with the specific animal
        self.animal = self.settings['animal']
        self.animals = self.settings['animals']
        # Database reference
        self.db = self.settings['db']
        # Collections references
        self.Animals = self.settings['db'][self.settings['animals'].lower()]
        self.Users = self.settings['db'].users
        self.Orgs = self.settings['db'].organizations
        self.Relatives = self.settings['db'].relatives
        self.ImageSets = self.settings['db'].imagesets
        self.Images = self.settings['db'].images
        self.CVRequests = self.settings['db'].cvrequests
        self.CVResults = self.settings['db'].cvresults
        self.cache = self.settings['cache']

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
                info(e)
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
            info(e)
            resp = False
        callback(resp)

    @engine
    def cache_read(self, key, prefix, callback=None):
        resp = None
        if key:
            val = self.cache.get(str(prefix) + '-' + str(key))
            if val:
                try:
                    resp = loads(val)
                except Exception as e:
                    info(e)
                    raise HTTPError('Fail to deserialize data from cache.')
        callback(resp)

    @engine
    def cache_set(self, key, prefix, data=None, ttl=432000, callback=None):
        resp = None
        if key and prefix and data:
            resp = self.cache.set(str(prefix) + '-' + str(key), dumps(data), ttl)
        callback(resp)

    @engine
    def cache_remove(self, key, prefix, callback=None):
        resp = None
        if key and prefix:
            resp = self.cache.delete(str(prefix) + '-' + str(key))
        callback(resp)

    def write_error(self, status_code=404, **kwargs):
        if status_code == 404:
            self.response(
                status_code, 'Resource not found.')
        elif status_code == 405:
            self.response(
                status_code, 'Method not allowed in this resource. ' +
                'Check your verb (GET, POST, PUT and DELETE).')
        else:
            info(kwargs)
            self.response(status_code, 'Error: ' + str(kwargs))

class VersionHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET')

    def get(self):
        self.response(200, self.settings['version'] + ' - animal defined: ' + self.animal)


class DocHandler(BaseHandler):
    SUPPORTED_METHODS = ('GET')

    def get(self):
        self.set_header('Content-Type', 'text/html; charset=UTF-8')
        self.render('documentation.html')

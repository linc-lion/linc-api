#!/usr/bin/env python3
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
from tornado.gen import coroutine, engine, Task
from handlers.base import BaseHandler
from datetime import datetime
from lib.rolecheck import api_authenticated
from logging import info
import functools


def check_relative_endpoint(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if args[1] != 'relatives':
            self.response(400, 'Invalid relative request.')
            return
        return method(self, *args, **kwargs)
    return wrapper


def api_authenticated(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        info('Remove this decorator later')
        return method(self, *args, **kwargs)
    return wrapper


class AnimalsRelativesHandler(BaseHandler):
    """ A class that handles requests about animals informartion """
    SUPPORTED_METHODS = ('GET', 'POST', 'PUT', 'DELETE')

    @asynchronous
    @coroutine
    @api_authenticated
    @check_relative_endpoint
    def get(self, animal_id=None, rurl=None, relid=None):
        relations = yield self.db.relatives.find({'id_from': int(animal_id)}).to_list(None)
        trelations = yield self.db.relatives.find({'id_to': int(animal_id)}).to_list(None)
        for obj in trelations:
            if obj['relation'] in ['suspected_father', 'mother']:
                obj['relation'] = 'cub'
        relations += trelations
        fmsg = 'for the id: %d' % int(animal_id)
        if relations:
            self.response(200, 'Relations found ' + fmsg, relations)
        else:
            self.response(404, 'Relations not found ' + fmsg)

    @engine
    def relation_is_valid(self, lobj, robj, relation, callback=None):
        # lobj = is the data object of the lion
        # robj = is the relative lion object
        valid_relations = [
            'mother', 'suspected_father', 'sibbling', 'associate']
        # check gender
        try:
            gender = yield self.db.imagesets.find_one({'iid': lobj['primary_image_set_iid']}, {'gender': 1})
            gender = gender.get('gender', None)
            if gender not in ['female', 'male']:
                gender = None
        except Exception as e:
            info(e)
            gender = None
        resp = None
        relation = relation.lower()
        if relation not in valid_relations or \
                (gender == 'female' and relation == 'suspected_father') or \
                (gender == 'male' and relation == 'mother'):
            resp = False, relation.lower(), gender
        else:
            resp = True, relation.lower(), gender
        callback(resp)

    @asynchronous
    @engine
    @check_relative_endpoint
    @api_authenticated
    def post(self, animal_id=None, rurl=None):
        lobj = yield Task(self.get_animal_by_id, animal_id)
        if not lobj:
            self.response(404, 'Animal not found for the id: ' + str(animal_id))
            return
        # check data
        id_from = animal_id
        id_to = self.input_data.get('relative_id', None)
        relation = self.input_data.get('relation', None)
        if not id_from or not id_to or not relation:
            self.response(400, 'Invalid request.')
            return
        try:
            robj = yield self.db[self.animals].find_one({'iid': int(id_to)})
        except Exception as e:
            info(e)
            robj = None
        if not robj:
            self.response(400, 'Relative not found with the id: %d' % (id_to))
            return
        already_relative_f = yield Task(self.check_relative, animal_id, id_to)
        already_relative_t = yield Task(self.check_relative, id_to, animal_id)
        already_relative = already_relative_f or already_relative_t
        if already_relative:
            self.response(409, 'Relation already defined.', already_relative)
            return
        valid, relation, gender = yield Task(self.relation_is_valid, lobj, robj, relation)
        if not valid:
            self.response(400, 'Invalid relationship assignment request with the relation: %s. (The individual with the id %d is a "%s" animal.)' % (relation, int(animal_id), gender))
            return
        try:
            radd = yield self.db.relatives.insert(
                {'id_from': int(animal_id),
                 'id_to': int(id_to),
                 'relation': relation.lower(),
                 'created_at': datetime.now(),
                 'updated_at': datetime.now()})
        except Exception as e:
            info(e)
            radd = None
        if radd:
            self.response(201, 'Relation added.')
        else:
            self.response(500, 'Fail to add relation.')

    @asynchronous
    @coroutine
    @check_relative_endpoint
    @api_authenticated
    def put(self, animal_id=None, rurl=None, relid=None):
        pass

    @asynchronous
    @coroutine
    @check_relative_endpoint
    @api_authenticated
    def delete(self, animal_id=None, rurl=None, relid=None):
        already_relative_f = yield Task(self.check_relative, animal_id, relid)
        already_relative_t = yield Task(self.check_relative, relid, animal_id)
        already_relative = already_relative_f or already_relative_t
        if already_relative:
            try:
                resp = self.db.relatives.remove(
                    {'id_from': already_relative['id_from'],
                     'id_to': already_relative['id_to']})
            except Exception as e:
                info(e)
                resp = None
            if resp:
                self.response(200, 'Relation removed.', already_relative)
            else:
                self.response(500, 'Fail to remove the relation.')
        else:
            self.response(404, 'Relation not found between the ids: %d -> %d' % (int(animal_id), int(relid)))

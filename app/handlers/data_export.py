from lib.rolecheck import api_authenticated
from base import BaseHandler
from collections import OrderedDict as odict
from logging import info
from tornado.gen import engine, Task, coroutine
from pymongo import ASCENDING
from tornado.web import asynchronous


class DataExportHandler(BaseHandler):
    SUPPORTED_METHODS = ('POST')

    def standard_keys(self):
        keys = odict()
        keys['_id'] = 'HashId'
        keys['iid'] = 'Id'
        keys['uploading_user_iid'] = 'Uploaded By'
        keys['notes'] = 'Notes'
        keys['tags'] = 'Tags'
        keys['owner_organization_iid'] = 'Owned By Org.'
        keys['uploading_organization_iid'] = 'Uploaded by Org.'
        keys['date_stamp'] = 'Datestamp'
        keys['date_of_birth'] = 'Date of Birth'
        keys['location'] = 'Location'
        keys['gender'] = 'Gender'
        keys['main_image_iid'] = 'Cover image Id'
        keys['is_verified'] = 'Verified'
        keys['created_at'] = 'Created'
        keys['updated_at'] = 'Updated'
        keys['animal_iid'] = self.animal.capitalize() + ' Id'
        return keys

    def check_structure(self, key, data):
        if key in data:
            if isinstance(data[key], list):
                if all([True if isinstance(x, int) else False for x in data[key]]):
                    return True
        return False

    @engine
    def get_data(self, idslist=None, animals=False, callback=None):
        keys = self.standard_keys()
        # current_user['organization_iid']
        resp = True
        try:
            fieldnames = list(keys.values())
            lines = list()
            cursor = self.ImageSets.find({'iid': {'$in': idslist}})
            cursor.sort([('iid', ASCENDING)])
            while (yield cursor.fetch_next):
                obj = cursor.next_object()
                rowdata = odict()
                for k, v in keys.items():
                    rowdata[v] = obj[k]
                lines.append(rowdata.copy())
            resp = {'fnames': fieldnames.copy(), 'lines': lines.copy()}
        except Exception as e:
            info(e)
            resp = False
        callback(resp)

    @asynchronous
    @coroutine
    @api_authenticated
    def post(self):
        animals = None
        if self.check_structure('lions', self.input_data):
            animals = True
        elif self.check_structure('imagesets', self.input_data):
            animals = False
        else:
            self.response(400, 'Invalid call.')
            return
        if animals:
            idslist = self.input_data['lions']
        else:
            idslist = self.input_data['imagesets']
        resp = yield Task(self.get_data, idslist=idslist, animals=animals)
        self.response(200, 'Data selected.', resp)

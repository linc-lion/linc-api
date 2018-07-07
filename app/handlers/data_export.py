from lib.rolecheck import api_authenticated
from base import BaseHandler
from collections import OrderedDict as odict
from logging import info
from tornado.gen import engine, Task, coroutine
from pymongo import ASCENDING
from tornado.web import asynchronous


class DataExportHandler(BaseHandler):
    SUPPORTED_METHODS = ('POST')

    def standard_keys(self, animal=False):
        keys = odict()

        if not animal:
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
        else:
            keys['_id'] = 'HashId'
            keys['name'] = 'Lion Name'
            keys['iid'] = 'Id'
            keys['organization_iid'] = 'Org. Id'
            keys['primary_image_set_iid'] = 'Primary ImageSet Id'
            keys['dead'] = 'Is Dead'
            keys['created_at'] = 'Created'
            keys['updated_at'] = 'Updated'

        return keys

    def check_structure(self, key, data):
        if key in data:
            if isinstance(data[key], list):
                if all([True if isinstance(x, int) else False for x in data[key]]):
                    return True
        return False

    @engine
    def get_data(self, idslist=None, animals=False, callback=None):
        keys = self.standard_keys(animals)
        info(keys)
        # current_user['organization_iid']
        # Collect data
        orgdata = yield self.Orgs.find({}, {'iid': 1, 'name': 1}).to_list(None)
        orgs = dict()
        for org in orgdata:
            orgs[org['iid']] = org['name']

        info(self.current_user)
        resp = True
        try:
            fieldnames = list(keys.values())
            lines = list()
            query = {'iid': {'$in': idslist}}
            if animals:
                cursor = self.Animals.find(query)
            else:
                cursor = self.ImageSets.find(query)
            cursor.sort([('iid', ASCENDING)])
            while (yield cursor.fetch_next):
                obj = cursor.next_object()
                rowdata = odict()
                for k, v in keys.items():
                    if k in obj:
                        rowdata[v] = obj[k]
                lines.append(rowdata.copy())
            info(lines)
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

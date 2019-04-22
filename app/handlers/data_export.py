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
            keys['animal_iid'] = self.animal.capitalize() + ' Id'
            keys['created_at'] = 'Created'
            keys['updated_at'] = 'Updated'
        else:
            keys['_id'] = 'HashId'
            keys['name'] = 'Lion Name'
            keys['iid'] = 'Id'
            keys['organization_iid'] = 'Org. Id'
            keys['primary_image_set_iid'] = 'Primary ImageSet Id'
            keys['dead'] = 'Is Dead'
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
        if self.current_user['role'] == 'admin':
            admin = True
        else:
            admin = False
        # Collect data
        gdata = yield self.Orgs.find({}, {'iid': 1, 'name': 1}).to_list(None)
        orgs = dict()
        for org in gdata:
            orgs[org['iid']] = org['name']
        gdata = yield self.Users.find({}, {'iid': 1, 'email': 1, 'admin': 1}).to_list(None)
        users = dict()
        for user in gdata:
            users[user['iid']] = {'email': user['email'], 'admin': user['admin']}
        gdata = yield self.Animals.find({}, {'iid': 1, 'name': 1}).to_list(None)
        animl = dict()
        for ani in gdata:
            animl[ani['iid']] = str(ani['iid']) + ' - ' + ani['name']
        resp = True
        # try:
        if True:
            fieldnames = list(keys.values())
            lines = list()
            query = {'iid': {'$in': idslist}}
            if animals:
                cursor = self.Animals.find(query)
            else:
                cursor = self.ImageSets.find(query)
            cursor.sort([('iid', ASCENDING)])
            imgsetids = list()
            while (yield cursor.fetch_next):
                obj = cursor.next_object()
                rowdata = list()
                for k, v in keys.items():
                    if k in obj and obj[k]:
                        if k in ['owner_organization_iid', 'uploading_organization_iid', 'organization_iid']:
                            value = orgs[obj[k]]
                        elif k == 'uploading_user_iid':
                            value = users[obj[k]]['email']
                        elif k == 'animal_iid':
                            value = animl.get(obj[k], '-') 
                        elif k == 'dead' and obj['dead']:
                            value = 'Yes'
                        elif k == 'dead' and not obj['dead']:
                            value = 'No'
                        else:
                            value = obj[k] if obj[k] else ' '
                        rowdata.append(value)
                    elif k == 'dead':
                        rowdata.append('No')
                    else:
                        rowdata.append(' ')
                if animals:
                    imgsetdata = yield self.ImageSets.find_one({'iid': obj['primary_image_set_iid']})
                    if imgsetdata:
                        for i in ['uploading_user_iid', 'notes', 'tags', 'owner_organization_iid', 'uploading_organization_iid', 'date_stamp', 'date_of_birth', 'location', 'gender', 'main_image_iid', 'is_verified']:
                            if i in ['owner_organization_iid', 'uploading_organization_iid', 'organization_iid']:
                                value = orgs[imgsetdata[i]]
                            elif i == 'uploading_user_iid':
                                value = users[imgsetdata[i]]['email']
                            elif i == 'animal_iid':
                                value = animl[imgsetdata[i]]
                            else:
                                value = imgsetdata[i] if imgsetdata[i] else ' '
                            rowdata.append(value)
                    for i in ['created_at', 'updated_at']:
                        rowdata.append(obj[i])
                lines.append(rowdata.copy())
                imgsetids.append(obj['iid'])
            lines.append([''])
            lines.append([''])
            for vid in imgsetids:
                if animals:
                    query_imgset = {'animal_iid': vid}
                else:
                    query_imgset = {'iid': vid}
                imgsetspl = yield self.ImageSets.find(query_imgset).to_list(None)
                # Check if the user's organization has the imageset or if the user is an admin
                for imset in imgsetspl:
                    if admin or int(imset['owner_organization_iid']) == int(self.current_user['org_id']):
                        lines.append(['Image Set: {} {}'.format(imset['iid'], ' - Lion: ' + animl[imset['animal_iid']] if imset['animal_iid'] else '')])
                        imgs = yield self.Images.find({'image_set_iid': imset['iid']}).to_list(None)
                        # ['_id', 'url', 'hashcheck', 'image_set_iid', 'created_at', 'image_tags', 'is_public', 'updated_at', 'iid', 'image_tags'])
                        lines.append(['HashId', 'Id', 'Image Set Id', 'Image Tags', 'Access', 'Created', 'Updated', 'Url'])
                        for objimg in imgs:
                            lines.append([
                                str(objimg['_id']),
                                objimg['iid'],
                                objimg['image_set_iid'],
                                objimg['image_tags'],
                                'PUBLIC' if objimg['is_public'] else 'PRIVATE',
                                objimg['created_at'],
                                objimg['updated_at'],
                                self.settings['S3_URL'] + objimg['url'] + '_full.jpg'
                            ])
                        lines.append([''])
                        lines.append([''])
            # Now the labels for lions
            if animals:
                for l in ['Uploaded by', 'Notes', 'Tags', 'Data Owner', 'Org. that Uploaded', 'Datestamp', 'Date of Birth', 'Location', 'Gender', 'Cover Image Id', 'Verified', 'Created', 'Updated']:
                    fieldnames.append(l)
            resp = {'fnames': fieldnames.copy(), 'lines': lines.copy()}
        # except Exception as e:
        else:
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

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
        keys['iid'] = 'Id'
        keys['name'] = 'Lion Name' if not animal else 'Name'
        keys['associated_id'] = 'Lion Id' if not animal else 'Imageset Id'
        keys['age'] = 'Age'
        keys['date_of_birth'] = 'Date of Birth'
        keys['dead'] = 'Dead'
        keys['organization'] = 'Organization'
        keys['gender'] = 'Gender'
        keys['latitude'] = 'Latitude'
        keys['longitude'] = 'Longitude'
        keys['tag_location'] = 'Location Tag'
        keys['geopos_private'] = 'GPS Points Private'
        keys['tags'] = 'Tag Features'
        keys['notes'] = 'Notes'
        keys['date_stamp'] = 'Date Stamp'
        keys['is_verified'] = 'Verified'
        keys['primary'] = "Primary"
        keys['link_to'] = "Link"
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
                if not animals:
                    imgset = obj
                    animal = None
                    if imgset['animal_iid']:
                        animal = yield self.Animals.find_one({ "iid": imgset['animal_iid']  })
                else:
                    animal = obj
                    imgset = None
                    if animal['primary_image_set_iid']:
                        imgset = yield self.ImageSets.find_one({ "iid": animal['primary_image_set_iid']  })
                    
                rowdata = list()
                for k, v in keys.items():
                    try:
                        if k == 'name':
                            name = animal['name'] if animal and animal['name'] else " "
                            rowdata.append(name)
                        elif k == 'associated_id':
                            rowdata.append(imgset['iid'] if animals else animal['iid'])
                        elif k == 'age':
                            if imgset and 'date_of_birth' in imgset and imgset['date_of_birth']:
                                age = self.age(imgset['date_of_birth'])
                                rowdata.append(age if age else ' ')
                            else:
                                rowdata.append(' ')
                        elif k == 'organization':
                            organization = None
                            if animal and 'organization_iid' in animal and animal['organization_iid']:
                                organization = yield self.Orgs.find_one({ "iid": animal['organization_iid'] })
                                
                            elif imgset:
                                if 'owner_organization_iid' in imgset and imgset['owner_organization_iid']:
                                    organization = yield self.Orgs.find_one({ "iid": imgset['owner_organization_iid'] })
                                elif 'uploading_organization_iid' in imgset and imgset['uploading_organization_iid']:
                                    organization = yield self.Orgs.find_one({ "iid": imgset['uploading_organization_iid'] })
                            rowdata.append(organization['name'] if organization and 'name' in organization and organization['name'] else ' ')
                        elif k == 'latitude':
                            rowdata.append(imgset['location'][0][0] if imgset and 'location' in imgset else ' ')
                        elif k == 'longitude':
                            rowdata.append(imgset['location'][0][1] if imgset and 'location' in imgset else ' ')
                        elif k == 'primary':
                            rowdata.append(True if animal and imgset and animal.get('primary_image_set_iid') == imgset.get('iid') else False)
                        elif k == 'link_to':
                            if animals:
                                rowdata.append('{}/#!/lion/{}'.format(self.settings['APP_URL'], animal['iid']))
                            else:
                                rowdata.append('{}/#!/imageset/{}'.format(self.settings['APP_URL'], imgset['iid']))
                        
                        elif k in obj:
                            rowdata.append(obj[k])
                        elif imgset and k in imgset:
                            rowdata.append(imgset[k])
                        elif animal and k in animal:
                            rowdata.append(animal[k])
                        else:
                            rowdata.append(' ')
                    except Exception as e:
                        rowdata.append(' ')
                lines.append(rowdata)
        
        resp = {'fnames': fieldnames.copy(), 'lines': lines.copy()}
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

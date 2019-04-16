from tornado.gen import engine, Task
from tornado.web import asynchronous
from models.user import User
from models.imageset import ImageSet
from bson import ObjectId as ObjId
from logging import info
from datetime import datetime
from schematics.exceptions import ValidationError


class DBMethods:

    def query_id(self, req_id):
        """The method configures the query to find an object."""
        query = None
        try:
            query = {'iid': int(req_id)}
        except Exception as e:
            try:
                query = {'_id': ObjId(req_id)}
            except Exception as e:
                query = {'name': str(req_id)}
        return query

    @asynchronous
    @engine
    def new_iid(self, collection, callback=None):
        iid = yield self.db.counters.find_one_and_update(
            filter={'_id': collection},
            update={'$inc': {'next': 1}},
            return_document=True, upsert=True)
        callback(int(iid['next']))

    @engine
    def get_org_by_id(self, orgid=None, callback=None):
        try:
            oobj = yield self.Orgs.find_one({'iid': orgid})
        except Exception as e:
            info(e)
            oobj = None
        callback(oobj)

    @engine
    def get_user_by_email(self, username=None, callback=None):
        try:
            uobj = yield self.Users.find_one({'email': username})
        except Exception as e:
            info(e)
            uobj = None
        callback(uobj)

    @engine
    def get_animal_by_id(self, animal_id, callback=None):
        try:
            lobj = yield self.Animals.find_one({'iid': int(animal_id)})
        except Exception as e:
            info(e)
            lobj = None
        callback(lobj)

    @engine
    def check_relative(self, animal_id, relative_id, callback=None):
        try:
            lobj = yield self.db.relatives.find_one({'id_from': int(animal_id), 'id_to': int(relative_id)})
        except Exception as e:
            info(e)
            lobj = None
        callback(lobj)

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
                saved = yield self.Users.update({'_id': updid}, updobj)
                info(saved)
                resp = [200, 'Password changed successfully.']
            except Exception as e:
                resp = [400, 'Fail to update password.']
        except ValidationError as e:
            resp = [400, 'Invalid input data. Errors: ' + str(e) + '.']
        callback(resp)

    @engine
    def create_imageset(self, input_data, callback=None):
        # Create a Imageset first
        newobj = dict()
        valid_fields = ImageSet._fields.keys()
        for k, v in input_data.items():
            if k in valid_fields:
                newobj[k] = v

        newobj['iid'] = yield Task(self.new_iid, ImageSet.collection())
        dt = datetime.now()
        newobj['created_at'] = dt
        newobj['updated_at'] = dt
        # validate the input
        fields_needed = ['uploading_user_id', 'uploading_organization_id', 'owner_organization_id',
                         'is_verified', 'gender', 'date_of_birth',
                         'tags', 'date_stamp', 'notes', self.animal + '_id', 'main_image_id', 'geopos_private']
        keys = list(input_data.keys())
        for field in fields_needed:
            if field not in keys:
                callback({'code': 400, 'message': 'You must provide the key for ' +
                          field + ' even it has the value = null.'})

        if newobj['date_stamp']:
            try:
                dts = datetime.strptime(
                    newobj['date_stamp'], "%Y-%m-%d").date()
                newobj['date_stamp'] = str(dts)
            except Exception as e:
                callback(
                    {'code': 400, 'message': 'Invalid date_stamp. you must provide it in format YYYY-MM-DD.'})

        if newobj['date_of_birth']:
            try:
                newobj['date_of_birth'] = datetime.strptime(
                    newobj['date_of_birth'], "%Y-%m-%d")
            except Exception as e:
                callback(
                    {'code': 400, 'message': 'Invalid date_of_birth. you must provide it in format YYYY-MM-DD.'})

        # check if user exists
        useriid = input_data['uploading_user_id']
        userexists = yield self.Users.find_one({'iid': useriid})
        if userexists:
            newobj['uploading_user_iid'] = useriid
        else:
            callback(
                {'code': 409, 'message': "Uploading user id referenced doesn't exist."})

        # check if organizations exists
        orgiid = input_data['uploading_organization_id']
        orgexists = yield self.db.organizations.find_one({'iid': orgiid})
        if orgexists:
            newobj['uploading_organization_iid'] = orgiid
        else:
            callback(
                {'code': 409, 'message': "Uploading organization id referenced doesn't exist."})

        oorgiid = input_data['owner_organization_id']
        oorgexists = yield self.db.organizations.find_one({'iid': oorgiid})
        if oorgexists['iid'] == oorgiid:
            newobj['owner_organization_iid'] = oorgiid
        else:
            callback(
                {'code': 409, 'message': "Owner organization id referenced doesn't exist."})

        if 'latitude' in input_data.keys() and input_data['latitude'] and \
                'longitude' in input_data.keys() and input_data['longitude']:
            newobj['location'] = [
                [input_data['latitude'], input_data['longitude']]]

        newobj['animal_iid'] = input_data[self.animal + '_id']

        try:
            newimgset = ImageSet(newobj)
            newimgset.validate()
            newobj = yield self.db.imagesets.insert(newimgset.to_native())
            output = newimgset.to_native()
            self.switch_iid(output)
            output['obj_id'] = str(newobj)
            output['owner_organization_id'] = output['owner_organization_iid']
            del output['owner_organization_iid']
            output['uploading_organization_id'] = output['uploading_organization_iid']
            del output['uploading_organization_iid']
            output['uploading_user_id'] = output['uploading_user_iid']
            del output['uploading_user_iid']
            output['main_image_id'] = output['main_image_iid']
            del output['main_image_iid']
            output[self.animal + '_id'] = output['animal_iid']
            del output['animal_iid']
            callback(
                {'code': 200, 'message': 'new image set added', 'data': output})
        except ValidationError as e:
            callback(
                {'code': 400, 'message': "Invalid input data. Error: " + str(e) + "."})

import json
from base64 import b64decode
from handlers.base import BaseHandler
import requests
import io
from os.path import realpath, dirname
from uuid import uuid4
from hashlib import md5
from logging import info
from models.imageset import Image
from tornado.gen import Task, engine
from json import dumps
from datetime import datetime
from schematics.exceptions import ValidationError
from lib.rolecheck import api_authenticated
from tornado.web import asynchronous
from PIL import Image as PILImage
from lib.image_utils import generate_images
from lib.upload_s3 import upload_to_s3
from os import remove




class AutoCropperUploadHandler(BaseHandler):

    def crop_and_show_image(self, image, coords):
        try:

            # Create a BytesIO object to read binary image data
            img_stream = io.BytesIO(image)

            # Open the image
            img = PILImage.open(img_stream)

            # Crop the image
            cropped_img = img.crop((coords[0], coords[1], coords[2], coords[3]))

            return cropped_img

        except Exception as e:
            print(f"An error occurred: {e}")


    def upload_image_s3(self, cropped_img_name, coordinates, imgid, imgobjid, folder_name, dt):

        fupdname =  dt.date().isoformat() + '_image_' + imgid + '_' + imgobjid
        generate_images(cropped_img_name)

        for suf in ['_full.jpg', '_icon.jpg', '_medium.jpg', '_thumbnail.jpg']:
            keynames3 = self.settings['S3_FOLDER'] + '/' + folder_name + '/' + fupdname + suf
            info(str(keynames3))
            f = open(cropped_img_name[:-4] + suf, 'rb')
            # self.s3con.upload(keynames3,f,expires=t,content_type='image/jpeg',public=True)
            resp = upload_to_s3(self.settings['S3_ACCESS_KEY'], self.settings['S3_SECRET_KEY'], f,  self.settings['S3_BUCKET'], keynames3)
            if resp:
                info('File upload OK: ' + str(keynames3))
            else:
                info('FAIL to upload: ' + str(keynames3))
            f.close()
            remove(cropped_img_name[:-4] + suf)

        self.remove_file(cropped_img_name)

    @asynchronous
    @engine
    @api_authenticated
    def post(self):

        if 'image' not in self.input_data.keys():
            self.response(400, 'The request to add image require the key \
                "image" with the file encoded with base64.')
            return
        if 'joined' in self.input_data.keys():
            self.response(400, 'The "joined" attribute can\'t be defined for a new image.')
            return
        # Check if its a valid image
        dirfs = dirname(realpath(__file__))
        imgname = dirfs + '/' + str(uuid4()) + '.img'

        try:
            fh = open(imgname, 'wb')
            fh.write(b64decode(self.input_data['image']))
            fh.close()
        except Exception as e:
            self.remove_file(imgname)
            self.response(400, 'The encoded image is invalid, \
                you must remake the encode using base64.')
            return
        # Ok, image is valid
        # Now, check if it already exists in the database
        image_file = open(imgname, 'rb').read()


        imgsetid = self.input_data['image_set_id']

        manual_coords = self.input_data['manual_coords']

        manual_coords_dict = json.loads(manual_coords)


        #####
        # everything checked, so good to go.
        #####
        # parse data recept by POST and get only fields of the object

        images_to_create = []

        for tag, values in manual_coords_dict['manual_coords'].items():
            images_to_create.append({
                tag: values
            })

        for values in manual_coords_dict['new_rect']:
            images_to_create.append({
                values['image_tags'][0]: values
            })


        for current_box_dict in images_to_create:
            for tag, values in current_box_dict.items():
                values['image_set_id'] = self.input_data['image_set_id']
                cropped_img = self.crop_and_show_image(image_file, values['coords'])
                cropped_img_name = dirfs + '/' + str(uuid4()) + '.jpg'
                cropped_img.save(cropped_img_name, 'JPEG')
                cropped_image_file = open(cropped_img_name, 'rb').read()

                filehash = md5(cropped_image_file).hexdigest()
                imgaexists = yield self.Images.find_one({'hashcheck': filehash})

                if imgaexists:
                    self.remove_file(cropped_img_name)
                    self.remove_file(imgname)
                    info('File already exists!')
                    self.response(409, 'The file already exists in the system.')

                isexists = yield self.ImageSets.find_one({'iid': imgsetid})

                newobj = self.parseInput(Image)
                # getting new integer id
                newobj['iid'] = yield Task(self.new_iid, Image.collection())
                # prepare new obj
                dt = datetime.now()
                newobj['created_at'] = dt
                newobj['updated_at'] = dt
                fields_needed = ['image_set_id', 'is_public', 'image_tags']
                for field in fields_needed:
                    newobj[field] = values[field]

                newobj['image_set_iid'] = imgsetid
                del newobj['image_set_id']

                try:
                    folder_name = 'imageset_' + str(isexists['iid']) + '_' + str(isexists['_id'])
                    url = folder_name + '/' + dt.date().isoformat() + '_image_' + str(newobj['iid']) + '_'
                    newobj['url'] = url
                    # adding the hash pre calculed
                    newobj['hashcheck'] = filehash
                    # info(newobj)
                    if 'exif_data' in newobj.keys() and isinstance(newobj['exif_data'], dict):
                        newobj['exif_data'] = dumps(newobj['exif_data'])
                    else:
                        info('No exif data found.')
                        newobj['exif_data'] = {}
                    # Force joined as None since only associated imagesets can have images joined to the primary imageset
                    newobj['joined'] = 0

                    newobj['is_auto_cropped'] = True

                    auto_coords = None
                    if tag in manual_coords_dict['auto_cropper_coords']:
                        auto_coords = manual_coords_dict['auto_cropper_coords'][tag]

                        newobj['auto_bounding_box_coords'] = {
                            tag: auto_coords
                        }

                    should_include_manual = not auto_coords or len(auto_coords) <= 0

                    if auto_coords:
                        for index in range(0, len(auto_coords)):
                            value1 = round(auto_coords[index], 3)
                            value2 = round(values['coords'][index], 3)
                            if value1 != value2:
                                should_include_manual = True
                                break

                    if should_include_manual:

                        newobj['manual_bounding_box_coords'] = {
                            tag: values['coords']
                        }

                    # info(newobj)
                    newimage = Image(newobj)
                    newimage.validate()
                    # the new object is valid, so try to save
                    try:
                        newsaved = yield self.Images.insert(newimage.to_native())
                        updurl = yield self.Images.update({'_id': newsaved}, {'$set': {'url': url + str(newsaved)}})
                        info(updurl)
                        output = newimage.to_native()
                        # File data saved, now start to
                        output['obj_id'] = str(newsaved)
                        output['url'] = url + str(newsaved)
                        output['image_set_id'] = output['image_set_iid']
                        del output['image_set_iid']
                        self.switch_iid(output)
                        # if is Cover
                        if values['iscover']:
                            updiscover = self.ImageSets.update(
                                {'iid': output['image_set_id']},
                                {'$set': {'updated_at': datetime.now(), 'main_image_iid': output['id']}})
                            info(updiscover)

                        # upload cropped image to s3 bucket
                        self.upload_image_s3(cropped_img_name, values['coords'], str(output['id']), output['obj_id'], folder_name, dt)


                    except ValidationError as e:
                        self.remove_file(imgname)
                        self.response(400, 'Fail to save image. Errors: ' + str(e) + '.')
                except ValidationError as e:
                    self.remove_file(imgname)
                    # received data is invalid in some way
                    self.response(400, 'Invalid input data. Errors: ' + str(e) + '.')



        # Remove Imageset Cache
        rem = yield Task(self.cache_remove, output['image_set_id'], 'imgset')
        # Returning success

        self.remove_file(imgname)
        self.response(201, 'New image saved. The image processing will start for this new image.', output)



class AutoCropperHandler(BaseHandler):

    #post method which takes image as input
    def post(self):

        url = self.settings['AUTOCROPPER_URL']

        payload = {}

        #get image from request
        files = {
            'file': (self.input_data['filename'], b64decode(self.input_data['image']), self.input_data['content_type'])
        }

        headers = {
            'Authorization': 'Bearer {}'.format(self.settings['AUTOCROPPER_TOKEN'])
        }

        response = requests.request("POST", url, headers=headers, data=payload, files=files)

        #return the response from the api
        self.set_status(200)
        self.finish(self.json_encode({'status': 'success', 'data': response.json()}))






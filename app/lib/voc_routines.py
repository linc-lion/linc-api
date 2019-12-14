#!/usr/bin/env python3.6
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
import os
import sys
import time
import zipfile
import hashlib
import logging
import shutil
import requests
#import xml.etree.ElementTree as ET

from json import loads
from PIL import Image
from lxml import etree
from collections import Counter
from logging import info
from logging import getLogger
from pathlib import Path
from logging import getLogger, StreamHandler, FileHandler, Formatter
from logging.handlers import WatchedFileHandler
from os.path import dirname, basename, splitext, abspath, isfile, exists, join, isdir, realpath
from base64 import b64encode
from lib.tags_map import classes, tag_key
from tornado.gen import coroutine, Task
from tornado.httputil import HTTPHeaders
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from requests import Request, Session
from json import dumps


# Path to log file from app folder
path_log = "lib/images.log"

voc_logger = getLogger("voc_logger")
voc_logger.setLevel(logging.INFO)

stream_handler = StreamHandler()

general_format = Formatter(fmt="[%(levelname)-6s %(asctime)s %(name)s %(lineno)4s ]"
                            " %(message)s", datefmt="%y%m%d %H:%M:%S")
stream_handler.setFormatter(general_format)

file_handler = FileHandler(path_log, "w")
file_handler.setFormatter(general_format)

voc_logger.addHandler(file_handler)
voc_logger.addHandler(stream_handler)


class AnnotatedImage:
    def __init__(self, img_path=None):

        self.img_path = img_path
        assert isfile(self.img_path), "Image path is not valid."
        self.json_path = splitext(img_path)[0] + ".json"
        assert isfile(self.json_path), "Image path is not valid."
        self.img_name = basename(self.img_path)
        self.voc_path = splitext(self.img_path)[0] + ".xml"
        self.voc_name = splitext(self.img_name)[0] + ".xml"
        self.result_images = []

    def delete(self):
        try:
            os.remove(self.img_path)
            os.remove(self.voc_path)
            os.remove(self.json_path)
        except Exception as e:
            voc_logger.error("Error when deleting image %s and associated voc file."
                            % basename(self.img_path)
                            )
            raise
        for img in self.result_images:
            try:
                os.remove(img)
            except Exception as e:
                voc_logger.error("Error when deleting image %s."
                                % basename(img)
                                )
                raise

    def validate_voc(self):
        XSD_path = "lib/PascalVOC_schema_justin.xsd"
        xmlschema_doc = etree.parse(XSD_path)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        xml_doc = etree.parse(self.voc_path)
        result = xmlschema.validate(xml_doc)
        return result

    def apply_voc(self):
        # Open Image
        im = Image.open(self.img_path)
        # Log image properties
        voc_logger.info("Format: %s \t Size: %s \t Mode: %s" % (im.format, im.size, im.mode))
        # Parse voc file
        tree = etree.parse(self.voc_path)
        root = tree.getroot()
        list_names = []
        i = 0

        for boxes in root.iter("object"):
            name = boxes.find("name").text
            # names = [item[0] for item in list_names]
            # try:
            #     i = names.index(name)
            #     list_names[i][1]+=1
            #     voc_logger.info("Name %s already exists. Renaming to %s", name,
            #                     list_names[i][0] + "_"
            #                     + str(list_names[i][1]))
            # except ValueError:
            #     list_names.append([name, 0])
            #     i = len(list_names) - 1

            ymin, xmin, ymax, xmax = None, None, None, None

            try:
                for box in boxes.findall("bndbox"):
                    ymin = float(box.find("ymin").text)
                    xmin = float(box.find("xmin").text)
                    ymax = float(box.find("ymax").text)
                    xmax = float(box.find("xmax").text)
            except ValueError as e:
                voc_logger.error("Value Error on file %s: " % basename(self.voc_path) + e.args[0])
                raise

            # voc_logger.info("%s" % (list_names[i][0] + "_" + \
            #             str(list_names[i][1])))
            # list_objects.append((name, (xmin, ymin, xmax, ymax)))

            region = im.crop((xmin, ymin, xmax, ymax))
            # region.save(join(dirname(self.img_path), list_names[i][0] + "_" + \
            #             str(list_names[i][1]) + ".jpg"))
            region.save(join(dirname(self.img_path), name + ".jpg"))
            self.result_images.append(join(dirname(self.img_path), name + ".jpg"))
        im.close()

    def call_api(self, _API_URL, headers):

        with open(self.json_path, "r") as jsonFile:
            metadata = loads(jsonFile.read())

        body = {
            "image_type": "",
            # "image_tags": image_tags,
            "is_public": metadata["is_public"],
            "image_set_id": int(metadata["image_set_id"]),
            "iscover": False,
            # "filename": fname,
            "exif_data": metadata["exif_data"],
            # "image": None
        }

        for img in self.result_images:
            with open(img, "rb") as imageFile:
                imgencoded = b64encode(imageFile.read())
                cod = classes.get(splitext(basename(img))[0], None)
                if cod:
                    info(cod)
                    tags = [v for k,v in tag_key.items() if cod in k]
                else:
                    info("Could not identify tag of image %s." % basename(img))
                    tags = []
                info(tags)
                body["image"] = imgencoded.decode("utf-8")
                body["image_tags"] = tags
                body["filename"] = basename(img)
                self.send_to_api(headers, body, _API_URL)

    def send_to_api(self, headers, body, _API_URL):
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        http_client = AsyncHTTPClient()
        dictheaders = {"content-type": "application/json"}
        if headers:
            for k, v in headers.items():
                dictheaders[k] = v
        info(dictheaders)
        h = HTTPHeaders(dictheaders)
        s = Session()
        prepped = Request('POST',
                        _API_URL + '/images/upload',
                        data=dumps(body),
                        headers=h
                        ).prepare()
        response = s.send(prepped,
                    verify=False,
                    timeout=720
                    )
        if response.status_code in [200, 201]:
            voc_logger.info('File successfully uploaded.')
        elif response.status_code == 409:
            voc_logger.error('The file already exists in the system.')
        elif response.status_code == 400:
            voc_logger.error('The data or file sent is invalid.')
        else:
            voc_logger.error('Fail to upload image.')

        return


@coroutine
def process_voc(inst, _dir=None, _API_URL=None, headers=None):

    path = dirname(realpath(__file__)) + "/uploaded_files" if _dir == None else _dir
    if os.path.exists(path):
        # path = sys.argv[1] if len(sys.argv)>1 else os.getcwd()
        image_files = []
        xml_files = []
        json_files = []
        other_files = []
        for filename in os.listdir(path):
            if splitext(filename)[1].lower() in [".jpg", ".png", ".jpeg", ".bmp", ".gif"]:
                image_files.append(path + "/" + filename)
            elif splitext(filename)[1] == ".xml":
                xml_files.append(path + "/" + filename)
            elif splitext(filename)[1] == ".json":
                json_files.append(path + "/" + filename)
            else:
                other_files.append(path + "/" + filename)

        voc_logger.info("Total number of files: %s" % (len(image_files)
                                                + len(xml_files)
                                                + len(json_files)
                                                + len(other_files)))

        voc_logger.info("Number of image files: %s" % len(image_files))
        voc_logger.info("Number of xml files: %s" % len(xml_files))
        voc_logger.info("Number of json files: %s" % len(json_files))
        voc_logger.info("Number of other files: %s" % len(other_files))

        # Iterate over image files.
        for img_path in image_files:
            # Take name of voc file.
            voc = os.path.splitext(img_path)[0] + ".xml"
            # Test whether voc exists.
            if os.path.isfile(voc):
                # Create instance of annotated image.
                image = AnnotatedImage(img_path)
                # Validade voc file.
                if image.validate_voc():
                    image.apply_voc()
                    image.call_api(_API_URL, headers)
                    # Removing original and resultant images as well as associated voc file.
                    time.sleep(2)
                    image.delete()
                else:
                    voc_logger.error("Voc file %s not valid." % basename(image.voc_path))
                    image.delete()
            # If voc file doesn't exists, delete image.
            else:
                voc_logger.error("%s does not have a voc file associated,"
                                " it will be deleted."
                                % os.path.basename(img_path))
                try:
                    os.remove(img_path)
                    os.remove(splitext(img_path)[0] + ".json")
                except Exception as e:
                    info(e)
                    voc_logger.error("Error on removing image file %s." % basename(img_path))
                    raise
        # Check voc files that do not have associated images and delete them.
        for voc_path in xml_files:
            if os.path.exists(voc_path):
                try:
                    os.remove(voc_path)
                except Exception as e:
                    info(e)
                    voc_logger.error("Error on removing voc file %s." % basename(voc_path))
                    raise
    else:
        voc_logger.info("Folder uploaded_files does not exist yet.")

    if hasattr(inst, "sendEmail"):
        msg = """Test email for voc files upload logging.""".encode('utf-8')
        resp = yield Task(inst.sendEmail, str(inst.current_user['username']), msg)
    time.sleep(5)
    info("Removing log file.")
    os.remove(path_log)
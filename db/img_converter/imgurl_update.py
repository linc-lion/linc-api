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

import pymongo as pm
from PIL import Image
from os import remove
from os.path import realpath,dirname

# To execute this script you need a ported version from the
# PostgreSQL database in MongoDB

# Connection to Mongo DB
try:
    conn=pm.MongoClient()
    print("MongoDB Connected successfully!!!")
except:
   print("Could not connect to MongoDB")
db = conn['linc-api-lions']

imgs = db.urlimages.find()
for img in imgs:
    imgobj = db.images.find_one({'iid':img['iid']})
    if imgobj:
        imgset = db.imagesets.find_one({'iid':imgobj['image_set_iid']})
        if imgset:
            folder_name = 'imageset_'+str(imgset['iid'])+'_'+str(imgset['_id'])
            fname = folder_name +'/' + str(imgobj['created_at'].date().isoformat()) + '_image_' + str(imgobj['iid']) + '_' + str(imgobj['_$
            upd = db.images.update({'_id':imgobj['_id']},{'$set' : {'url':fname}})
            print(upd)
    else:
        print 'Image without imageset: ',img

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
from os import remove
from os.path import realpath,dirname
from hashlib import md5

# Connection to Mongo DB
try:
    conn=pm.MongoClient()
    print("MongoDB Connected successfully!!!")
except:
   print("Could not connect to MongoDB")
db = conn['linc-api-lions']

import urllib
from datetime import timedelta
t = timedelta(days=1)
# Getting info about the folder
imgsl = db.urlimages.find()
for imgobj in imgsl:
    imgurl = imgobj['url']
    fn = imgurl.split('/')[-1]
    urllib.urlretrieve(imgurl,fn)
    imgdata = open(fn).read()
    filehash = md5(imgdata).hexdigest()
    upl = db.md5hashs.insert({'iid':imgobj['iid'],'hash':filehash})
    remove(fn)

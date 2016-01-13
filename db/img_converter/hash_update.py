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

# Connection to Mongo DB
try:
    conn=pm.MongoClient()
    print("MongoDB Connected successfully!!!")
    print conn
except:
   print("Could not connect to MongoDB")

db = conn['linc-api-lions']
print db
imgs = db.images.find()
for img in imgs:
    imgobj = db.md5hashs.find_one({'iid':img['iid']})
    print imgobj
    if imgobj:
        upd = db.images.update({'_id':img['_id']},{'$set' : {'hashcheck':imgobj['hash']}})
        print upd

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
    imgset = db.imagesets.find_one({'iid':imgobj['image_set_iid']})
    if imgset:
        folder_name = 'imageset_'+str(imgset['iid'])+'_'+str(imgset['_id'])
        fname = folder_name +'/' + str(imgobj['created_at'].date().isoformat()) + '_image_' + str(imgobj['iid']) + '_' + str(imgobj['_id'])
        #print(fname)
        upd = db.images.update({'_id':imgobj['_id']},{'$set' : {'url':fname}})
        print(upd)

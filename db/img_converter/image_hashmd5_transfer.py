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

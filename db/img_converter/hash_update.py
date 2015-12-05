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

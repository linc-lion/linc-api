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

"""
imgset = db.imagesets.find()
apidir = 'linc-api-lions/'
for iset in imgset:
    print('Processing Image Set: '+str(iset['iid']))
    folder_name = 'imageset_'+str(iset['iid'])+'_'+str(iset['_id'])
    #print('Folder name:' + folder_name)
    nupd = db.uploaded.find()
    lnupd = [x['iid'] for x in nupd ]
    imgs = db.images.find({'image_set_iid':iset['iid'],'iid': {'$nin':lnupd}})
    for img in imgs:
        print('Processing Image: '+str(img['iid']))
        iurl = db.urlimages.find_one({'iid':img['iid']})
        imgurl = iurl['url']
        imgname = str(img['created_at'].date().isoformat()) + '_image_' + str(img['iid']) + '_' + str(img['_id']) + ".img"
        print('Getting image: '+imgurl)
        urllib.urlretrieve(imgurl, imgname)


        generate_images(imgname)
        for suf in ['_full.jpg','_icon.jpg','_medium.jpg','_thumbnail.jpg']:
            keynames3 = apidir + folder_name + '/' + str(img['created_at'].date().isoformat()) + '_image_' + str(img['iid']) + '_' + str(img['_id']) + suf
            f = open(imgname[:-4]+suf,'rb')
            conns3.upload(keynames3,f,expires=t,content_type='image/jpeg',public=True)
            f.close()
            remove(imgname[:-4]+suf)
        upl = db.uploaded.insert({'iid':img['iid']})
"""
"""
print("Checking images that was not uploaded")
d = db.uploaded.find({},{'_id':0,'iid':1})
upds = [e['iid'] for e in d]
stnupd = db.urlimages.find({'iid': { '$nin' : upds}})
for o in stnupd:
    # Get the image object
    img = db.images.find_one({'iid':o['iid']})
    # Get the imageset object
    imst = db.imagesets.find_one({'iid':img['image_set_iid']})
    print(img)
    print(imst)
    break
"""

import pymongo as pm
from PIL import Image
from os import remove
from os.path import realpath,dirname

# Connection to Mongo DB
try:
    conn=pm.MongoClient()
    print("MongoDB Connected successfully!!!")
except:
   print("Could not connect to MongoDB")
db = conn['linc-api-lions']

import tinys3
# Creating a simple connection
S3_ACCESS_KEY = 'AKIAJLWIXAYAEIRLYYFA'
S3_SECRET_KEY = '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'
S3_BUCKET = 'linc-test'

conns3 = tinys3.Connection(S3_ACCESS_KEY,S3_SECRET_KEY,default_bucket=S3_BUCKET)

def generate_images(fn):
    if '.jpeg' in fn:
        fn = fn[:-5]+jpg
    # Saving the full image as JPEG
    im = Image.open(fn)
    im.save(fn[:-4]+'_full.jpg','JPEG',quality=100)
    # Crop 1:1
    im = Image.open(fn)
    width, height = im.size
    print(im.size)
    nheight = height
    nwidth = width
    if width < height:
        nheight = width
        left = 0
        top = int((height-nheight)/2)
        right = int(width)
        bottom = int((height-nheight)/2 + nheight)
    else:
        nwidth = int(height)
        left = int((width-nwidth)/2)
        top = 0
        right = int((width-nwidth)/2 + nwidth)
        bottom = height
    im.crop((left,top,right,bottom)).save(fn[:-4]+'_crop.jpg','JPEG')
    im.close()
    # Making thumbnail = 160x160 = CSS Square
    im = Image.open(fn[:-4]+'_crop.jpg')
    im.thumbnail((160,160))
    im.save(fn[:-4]+'_thumbnail.jpg',"JPEG")
    im.close()
    # Create medium 600x or x600
    im = Image.open(fn)
    w,h = im.size
    newsize = 600
    if w < h:
        # h is the reference
        r = newsize/h
        neww = w*r
        msize = neww,newsize
    elif h < w:
        # w is the reference
        r = newsize/w
        newh = h*r
        msize = newsize,newh

    if msize[1] == 0 or msize[1] == 0:
        msize = newsize,newsize
    print(msize)
    im.thumbnail(msize)
    im.save(fn[:-4]+'_medium.jpg',"JPEG")
    im.close()
    # Saving the icon 40x40
    im = Image.open(fn[:-4]+'_crop.jpg')
    im.thumbnail((40,40))
    im.save(fn[:-4]+'_icon.jpg',"JPEG")
    im.close()
    remove(fn[:-4]+'_crop.jpg')
    remove(fn)

import urllib
from datetime import timedelta
t = timedelta(days=1)
# Getting info about the folder
imgset = db.imagesets.find()
apidir = 'linc-api-lions/'
for i in imgset:
    folder_name = 'imageset_'+str(i['iid'])+'_'+str(i['_id'])
    #print('Folder name:' + folder_name)
    imgs = db.images.find({'image_set_iid':i['iid']})
    for img in imgs:
        iurl = db.urlimages.find_one({'iid':i['iid']})
        imgurl = iurl['url']
        print(imgurl)
        imgname = str(img['created_at'].date().isoformat()) + '_image_' + str(img['iid']) + '_' + str(img['image_type']) + '_' + str(img['_id']) + ".img"
        print(imgname)
        urllib.urlretrieve(imgurl, imgname)

        generate_images(imgname)
        for suf in ['_full.jpg','_icon.jpg','_medium.jpg','_thumbnail.jpg']:
            keynames3 = apidir + folder_name + '/' + str(img['created_at'].date().isoformat()) + '_image_' + str(img['iid']) + '_' + str(img['image_type']) + '_' + str(img['_id']) + suf
            f = open(imgname[:-4]+suf,'rb')
            conns3.upload(keynames3,f,expires=t,content_type='image/jpeg',public=True)
            f.close()
            remove(imgname[:-4]+suf)

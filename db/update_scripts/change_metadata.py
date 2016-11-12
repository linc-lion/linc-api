

from pymongo import MongoClient
conn = MongoClient("mongodb://localhost:27017")
db = conn['linc-api-lions']

from bson import ObjectId as oi
from json import dumps,loads

for obj in db.imagesets.find({}):
    objid = obj['_id']
    print(obj['tags'])
    tags = loads(obj['tags'])
    print(tags)
    if tags == None:
        print('=====================')
        continue
    ntags = list()
    for tag in tags:
        if tag in ['EYE_DAMAGE_LEFT','EYE_DAMAGE_RIGHT','EYE_DAMAGE_BOTH']:
            ntags.append('EYE_DAMAGE_YES')
        elif tag in ['MOUTH_MARKING_BACK','MOUTH_MARKING_FRONT','MOUTH_MARKING_LEFT','MOUTH_MARKING_RIGHT']:
            ntags.append('MOUTH_MARKING_YES')
        else:
            ntags.append(tag)
    print(tags)
    print(ntags)
    print('=====================')
    res = db.imagesets.update({'_id':objid},{'$set':{'tags':dumps(ntags)}},upsert=False)
    print(res)

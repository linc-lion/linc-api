from tornado.httpclient import AsyncHTTPClient,HTTPRequest,HTTPError
from tornado import gen
from tornado.web import asynchronous
from tornado.escape import json_decode
from logging import info
from datetime import datetime
from json import dumps,loads
#from tinys3 import Connection as s3con
from tinys3 import Pool as s3con

@gen.coroutine
def checkS3(db,api):
    # Get list for DELETE
    dellist = db.dellist.find()
    dellist = [x for x in dellist]
    if len(dellist) > 0:
        # Connect to S3
        S3_ACCESS_KEY = api['S3_ACCESS_KEY']
        S3_SECRET_KEY = api['S3_SECRET_KEY']
        S3_BUCKET = api['S3_BUCKET']
        try:
            conn = s3con(S3_ACCESS_KEY,S3_SECRET_KEY,default_bucket=S3_BUCKET,size=20)
            print('\nConnected to S3')
        except:
            print('\nFail to connect to S3')
            return
        for rmlist in dellist:
            if rmlist['list']:
                print 'Removing files from: '+str(rmlist['ts'])
                reqs = list()
                try:
                    for key in rmlist['list']:
                        print key
                        print S3_BUCKET
                        reqs.append(conn.delete(key,S3_BUCKET))
                    conn.all_completed(reqs)
                    res = db.dellist.remove({'_id':rmlist['_id']})
                except:
                    print '\n\nError in the deletion of images'

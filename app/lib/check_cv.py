from tornado.httpclient import AsyncHTTPClient,HTTPRequest,HTTPError
from tornado.escape import json_decode
from logging import info
from datetime import datetime
from json import dumps

def checkresults(db,api):
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    # Get ids with status != finished or error
    cvreqs = db.cvrequests.find({'status':{'$nin':['finished','error']}})
    #cvreqs = db.cvrequests.find({'server_uuid':'1a4db675-6fef-4e44-8bb2-18fbc80b7739'})
    # Check if cvresults exists
    for cvreq in cvreqs:
        #print 'Request ID: '+str(cvreq_id)
        #info('Request ID: '+str(cvreq_id))
        cvres = db.cvresults.find_one({'cvrequest_iid':cvreq['iid']})
        if not cvres:
            # Create the CVResults
            iid = db.counters.find_and_modify(query={'_id':'cvresults'}, update={'$inc' : {'next':1}}, new=True, upsert=True)
            newcvres = dict()
            newcvres['cvrequest_iid'] = cvreq['iid']
            newcvres['iid'] = iid['next']
            newcvres['match_probability'] = '[]'
            dt = datetime.now()
            newcvres['created_at'] = dt
            newcvres['updated_at'] = dt
            ncvresobjid = db.cvresults.insert(newcvres)
            print 'Results ID created: '+str(ncvresobjid)
            info('Request ID created: '+str(ncvresobjid))
        # Cvres exists, so try to get data
        http_client = AsyncHTTPClient()
        url = api['CVSERVER_URL_RESULTS']+cvreq['server_uuid']
        if url == '':
            info('\nFail to get CVSERVER_URL_RESULTS... Stopping process...')
            print '\nFail to get CVSERVER_URL_RESULTS... Stopping process...'
            return
        request = HTTPRequest(**{
            'url' : url,
            'method' : 'GET',
            'auth_username' : api['CV_USERNAME'],
            'auth_password' : api['CV_PASSWORD'],
            'request_timeout': 720,
            'validate_cert' : False
        })
        def handle_request(response):
            dt = datetime.now()
            if response.error:
                print "Error:", response.error
                db.cvrequests.update({'_id':cvreq['_id']},{'$set':{'status':'fail','updated_at':dt}})
            else:
                print 'Connection OK'
                rbody = json_decode(response.body)
                rbody['code'] = response.code
                rbody['reason'] = response.reason
                print(rbody)
                nstatus = rbody['status']
                mresult = dumps(rbody['lions'])
                print 'CV Req Status: '+nstatus
                print 'match_probability: '+mresult
                db.cvrequests.update({'_id':cvreq['_id']},{'$set':{'status':nstatus,'updated_at':dt}})
                db.cvresults.update({'_id':cvres['_id']},{'$set':{'match_probability':mresult,'updated_at':dt}})
        try:
            http_client.fetch(request,handle_request)
        except HTTPError, e:
            print('errors: '+str(e))

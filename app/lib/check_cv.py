from tornado.httpclient import AsyncHTTPClient,HTTPRequest,HTTPError
from tornado import gen
from tornado.escape import json_decode
from logging import info
from datetime import datetime
from json import dumps

@gen.coroutine
def checkresults(db,api):
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    # Clear cvresults without cvrequests
    cvreqs = db.cvrequests.find()
    lcvreqids = [x['iid'] for x in cvreqs]
    rmcv = db.cvresults.remove({'cvrequest_iid':{'$nin':lcvreqids}},multi=True)
    # Get ids with status != finished or error
    cvreqs = db.cvrequests.find({'status':{'$nin':['finished','error']}})
    cvreqs = [x for x in cvreqs]
    print 'CVReqs count: ',str(len(cvreqs))

    #cvreqs = db.cvrequests.find({'server_uuid':'1a4db675-6fef-4e44-8bb2-18fbc80b7739'})
    # Check if cvresults exists
    for cvreq in cvreqs:
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
        try:
            #http_client.fetch(request,callback=lambda response:handle_request(response, cvreq, db))
            #resp = fetch_coroutine(request)
            dt = datetime.now()
            info(" ### Checking CV Request: "+str(cvreq['iid'])+" ###")
            response = yield http_client.fetch(request)
            print 'Connection OK'
            rbody = json_decode(response.body)
            rbody['code'] = response.code
            rbody['reason'] = response.reason
            nstatus = rbody['status']
            if nstatus == 'done':
                nstatus = 'finished'
            mresult = dumps(rbody['lions'])
            print rbody
            #print 'CV Req Status: '+nstatus
            #print 'match_probability: '+mresult
            db.cvrequests.update({'_id':cvreq['_id']},{'$set':{'status':nstatus,'updated_at':dt}})
            db.cvresults.update({'cvrequest_iid':cvreq['iid']},{'$set':{'match_probability':mresult,'updated_at':dt}})
        except HTTPError, e:
            print 'HTTTP error returned... '
            print "Code: ", e.code
            print "Message: ", e.message
            if e.response:
                print 'URL: ', e.response.effective_url
                print 'Reason: ', e.response.reason
                print 'Body: ', e.response.body
            db.cvrequests.update({'_id':cvreq['_id']},{'$set':{'status':'fail','updated_at':dt}})
        except Exception as e:
            # Other errors are possible, such as IOError.
            print("Other Errors: " + str(e))

"""
def handle_request(response,cvreq,db):
    dt = datetime.now()
    #print "\n ### Checking CV Request: "+str(cvreq['iid'])+" ###"
    info(" ### Checking CV Request: "+str(cvreq['iid'])+" ###")
    info("URL:"+str(response.effective_url))
    info("CVreq:"+str(cvreq['iid']))
    info("DB:"+str(db))
    dt = datetime.now()
    if response.error:
        print "Error:", response.error
        print "Body:", response.body
        print "Code:", response.code
        print "Reason:", response.reason
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
        db.cvresults.update({'cvrequest_iid':cvreq['iid']},{'$set':{'match_probability':mresult,'updated_at':dt}})
"""

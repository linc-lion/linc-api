#!/usr/bin/env python3
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

from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from tornado.httputil import HTTPHeaders
from tornado import gen
from logging import info
from datetime import datetime
from json import dumps, loads
from time import time


@gen.coroutine
def checkresults(db, api):
    ini = time()
    info('=========================================================================')
    info(' Starting CV Request processing - {}'.format(datetime.now().isoformat()))
    info('=========================================================================')
    # Check results execute GET in the CV Server URL to acquire results for cv requests
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    http_client = AsyncHTTPClient()
    cvreqs = db.cvrequests.find()
    # retrieve data from the cursor
    lcvreqids = [x['iid'] for x in cvreqs]
    rmcv = db.cvresults.remove({'cvrequest_iid': {'$nin': lcvreqids}}, multi=True)
    info('    Clear cvresults without cvrequests: {}'.format(rmcv))
    # Get ids with status != finished or error
    cvreqs = db.cvrequests.find({'status': {'$nin': ['finished', 'error']}})
    # retrieve data from the cursor
    cvreqs = [x for x in cvreqs]
    info('    CV Request not finished of error - count: ' + str(len(cvreqs)))
    # Connection preset
    params = {
        'headers': HTTPHeaders({"content-type": "application/json", "ApiKey": api['CV_APIKEY']}),
        'url': api['CVSERVER_URL'] + '/linc/v1/classify',
        'method': 'POST',
        'body': '',
        'request_timeout': 5,
        'validate_cert': False}
    # Check if cvresults exists
    for cvreq in cvreqs:
        info("========================================================================")
        info(" ### Checking CV Request: " + str(cvreq['iid']) + " ###")
        info("  ## Image set submitted: " + str(cvreq['image_set_iid']) + " ##")
        cvres = db.cvresults.find_one({'cvrequest_iid': cvreq['iid']})
        # Restart after 10 minutes
        if cvres:
            info('  >> Created at: {}'.format(cvres['created_at']))
            info('  >>        now: {}'.format(datetime.now()))
            if (datetime.now() - cvres['created_at']).seconds > 7200:
                #info("  !!! The recognition process took more than 10 minutes... restarting")
                info("!!! The CV Request took more than 2 hours to finish")
                info("!!! Marking it with error status")
                db.cvrequests.update({'iid': cvreq['iid']}, {'$set': {'status': 'error', 'updated_at': datetime.now()}})
                cvrem_restart = db.cvresults.remove({'cvrequest_iid': cvreq['iid']})
                cvres = None
                info("========================================================================")
                continue
        if not cvres:
            # Create the CVResults
            iid = db.counters.find_and_modify(
                query={'_id': 'cvresults'},
                update={'$inc': {'next': 1}},
                new=True,
                upsert=True)
            newcvres = dict()
            newcvres['cvrequest_iid'] = cvreq['iid']
            newcvres['iid'] = iid['next']
            newcvres['match_probability'] = '{}'
            dt = datetime.now()
            newcvres['created_at'] = dt
            newcvres['updated_at'] = dt
            ncvresobjid = db.cvresults.insert(newcvres)
            info('CV results created id: ' + str(ncvresobjid))
            cvres = db.cvresults.find_one({'cvrequest_iid': cvreq['iid']})
        # Cvres exists, so try to get data
        info('  ## CV Results id.....: {}  ## '.format(cvres['iid']))
        req_body = loads(cvreq['request_body'])
        resp_cvr = loads(cvres['match_probability'])
        if len(resp_cvr) == 0:
            resp_cvr['cv'] = list()
            resp_cvr['whisker'] = list()
        # Check for cv results
        # cv_topk_classifier_accuracy
        # whisker_topk_classifier_accuracy
        if not req_body.get('classifiers', False):
            info(' >>> CV Request invalid - id: {}'.format(cvreq['iid']))
            info(' >>> No classifiers found.')
        else:
            # Check CV
            finished = {'cv': 0, 'whisker': 0}
            for clf in ['cv', 'whisker']:
                if req_body['classifiers'].get(clf, False):
                    info('    Processing calls for the classifier {}'.format(clf.upper()))
                    add = len(resp_cvr[clf]) == 0
                    if add:
                        # Submit requests
                        for n, clf_call in enumerate(req_body[clf + '_calls']):
                            dparams = params.copy()
                            dparams['body'] = dumps(clf_call)
                            request = HTTPRequest(**dparams)
                            try:
                                response = yield http_client.fetch(request)
                            except HTTPError as e:
                                info(e)
                                response = e.response
                            except Exception as e:
                                info(e)
                                response = None
                            if response and response.code in [200, 201]:
                                info('          Call {} #{} - success'.format(clf.upper(), n))
                                resp_cvr[clf].append(loads(response.body.decode('utf-8')))
                            else:
                                info('          Call {} #{} - fail'.format(clf.upper(), n))
                                resp_cvr[clf].append('FAILURE')
                    else:
                        # Check results
                        for n, clf_call in enumerate(req_body[clf + '_calls']):
                            info(resp_cvr[clf][n])
                            # {'id': '432f7612-8b7d-4132-baae-f93f094abb7f', 'status': 'PENDING', 'errors': []}
                            if isinstance(resp_cvr[clf][n], dict) and resp_cvr[clf][n].get('status', None) == 'finished':
                                info('          Request CV #{} finished'.format(n))
                                finished[clf] += 1
                            else:
                                info('       Check results for CV #{}'.format(n))
                                dparams = params.copy()
                                del dparams['body']
                                dparams['method'] = 'GET'
                                url = api['CVSERVER_URL'] + '/linc/v1/results/' + resp_cvr[clf][n]['id']
                                info('       {}'.format(url))
                                dparams['url'] = url
                                request = HTTPRequest(**dparams)
                                try:
                                    response = yield http_client.fetch(request)
                                except HTTPError as e:
                                    info(e)
                                    response = e.response
                                except Exception as e:
                                    info(e)
                                    response = None
                                if response.code in [200, 201]:
                                    info('          Call #{} - success'.format(n))
                                    resp_data = loads(response.body.decode('utf-8'))
                                    info('          Status: {}'.format(resp_data['status']))
                                    if resp_data['status'] == 'finished':
                                        resp_cvr[clf][n] = resp_data.copy()
                                else:
                                    info('          Call #{} - fail'.format(n))
            dt = datetime.now()
            if finished['cv'] == len(req_body['cv_calls']) and finished['whisker'] == len(req_body['whisker_calls']):
                info(' Loading capabilities...')
                dparams = params.copy()
                del dparams['body']
                dparams['method'] = 'GET'
                dparams['url'] = api['CVSERVER_URL'] + '/linc/v1/capabilities'
                request = HTTPRequest(**dparams)
                try:
                    response = yield http_client.fetch(request)
                except HTTPError as e:
                    info(e)
                    response = e.response
                except Exception as e:
                    info(e)
                    response = None
                if response.code in [200, 201]:
                    info(' ### CV Request finished ###')
                    db.cvrequests.update({'iid': cvreq['iid']}, {'$set': {'status': 'finished', 'updated_at': dt}})
                    resp_cvr['capabilities'] = loads(response.body.decode('utf-8'))
                    resp_cvr['execution'] = dt.timestamp() - cvres['created_at'].timestamp()
                else:
                    info(' Fail to retrieve capabilities info...')
            db.cvresults.update({'cvrequest_iid': cvreq['iid']}, {'$set': {'match_probability': dumps(resp_cvr), 'updated_at': dt}})
            api['cache'].delete('imgset-' + str(cvreq['image_set_iid']))
            info('   Cache delete for image set id: {}'.format(cvreq['image_set_iid']))
    info('=========================================================================')
    info(' CV Request processing finished - Execution time: {0:.2f} s'.format(time() - ini))
    info('=========================================================================')

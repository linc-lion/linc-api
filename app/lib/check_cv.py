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
    lcvreqids = [x['iid'] for x in cvreqs]
    rmcv = db.cvresults.remove({'cvrequest_iid': {'$nin': lcvreqids}}, multi=True)
    info('    Clear cvresults without cvrequests: {}'.format(rmcv))
    # Get ids with status != finished or error
    cvreqs = db.cvrequests.find({'status': {'$nin': ['finished', 'error']}})
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
        info(" ### Checking CV Request: " + str(cvreq['iid']) + " ###")
        info("  ## Image set submitted: " + str(cvreq['image_set_iid']) + " ##")
        cvres = db.cvresults.find_one({'cvrequest_iid': cvreq['iid']})
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
            newcvres['match_probability'] = '[]'
            dt = datetime.now()
            newcvres['created_at'] = dt
            newcvres['updated_at'] = dt
            ncvresobjid = db.cvresults.insert(newcvres)
            info('CV results created id: ' + str(ncvresobjid))
            cvres = db.cvresults.find_one({'cvrequest_iid': cvreq['iid']})
        # Cvres exists, so try to get data
        req_body = loads(cvreq['request_body'])
        resp_cv = loads(cvres['match_probability'])
        if len(resp_cv) == 0:
            resp_cv.append({'type': 'cv', 'results': list()})
            resp_cv.append({'type': 'whisker', 'results': list()})
        # Check for cv results
        # cv_topk_classifier_accuracy
        # whisker_topk_classifier_accuracy
        if not req_body.get('classifiers', False):
            info(' >>> CV Request invalid - id: {}'.format(cvreq['iid']))
            info(' >>> No classifiers found.')
        else:
            # Check CV
            cv_finished = 0
            wh_finished = 0
            if req_body['classifiers'].get('cv', False):
                info('    Processing calls for the classifier CV')
                add = len(resp_cv[0]['results']) == 0
                if add:
                    for n, cv_call in enumerate(req_body['cv_calls']):
                        dparams = params.copy()
                        dparams['body'] = dumps(cv_call)
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
                            info('          Call #{} - success'.format(n))
                            resp_cv[0]['results'].append(loads(response.body.decode('utf-8')))
                        else:
                            info('          Call #{} - fail'.format(n))
                            resp_cv[0]['results'].append('FAILURE')
                else:
                    # Check results
                    for n, cv_call in enumerate(req_body['cv_calls']):
                        if resp_cv[0]['results'][n].get('status', None) == 'finished':
                            info('          Request CV #{} finished'.format(n))
                            cv_finished += 1
                        else:
                            info('       Check results for CV #{}'.format(n))
                            dparams = params.copy()
                            del dparams['body']
                            dparams['method'] = 'GET'
                            url = api['CVSERVER_URL'] + '/linc/v1/results/' + resp_cv[0]['results'][n]['id']
                            info(url)
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
                                if resp_data['status'] == 'finished':
                                    resp_cv[0]['results'][n] = resp_data.copy()
                            else:
                                info('          Call #{} - fail'.format(n))

            if req_body['classifiers'].get('whisker', False):
                info('    Processing calls for the classifier Whisker')
                add = len(resp_cv[1]['results']) == 0
                if add:
                    for n, wh_call in enumerate(req_body['wh_calls']):
                        dparams = params.copy()
                        dparams['body'] = dumps(wh_call)
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
                            resp_cv[1]['results'].append(loads(response.body.decode('utf-8')))
                        else:
                            info('          Call #{} - fail'.format(n))
                            resp_cv[1]['results'].append('FAILURE')
                else:
                    # Check results
                    for n, wh_call in enumerate(req_body['wh_calls']):
                        if resp_cv[1]['results'][n].get('status', None) == 'finished':
                            info('          Request Whisker #{} finished'.format(n))
                            wh_finished += 1
                        else:
                            info('     Check results for Whisker #{}'.format(n))
                            dparams = params.copy()
                            del dparams['body']
                            dparams['method'] = 'GET'
                            url = api['CVSERVER_URL'] + '/linc/v1/results/' + resp_cv[1]['results'][n]['id']
                            info(url)
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
                                if resp_data['status'] == 'finished':
                                    resp_cv[1]['results'][n] = resp_data.copy()
                            else:
                                info('          Call #{} - fail'.format(n))
            dt = datetime.now()
            if cv_finished == len(req_body['cv_calls']) and wh_finished == len(req_body['wh_calls']):
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
                    resp_cv.append({'capabilities': loads(response.body.decode('utf-8'))})
                else:
                    info(' Fail to retrieve capabilities info...')
            db.cvresults.update({'cvrequest_iid': cvreq['iid']}, {'$set': {'match_probability': dumps(resp_cv), 'updated_at': dt}})
            api['cache'].delete('imgset-' + str(cvreq['image_set_iid']))
            info('   Cache delete for image set id: {}'.format(cvreq['image_set_iid']))
    info('=========================================================================')
    info(' CV Request processing finished - Execution time: {0:.2f} s'.format(time() - ini))
    info('=========================================================================')

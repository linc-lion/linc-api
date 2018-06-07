from tornado.web import asynchronous
from tornado.gen import engine
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from tornado.httputil import HTTPHeaders
from logging import info


class HTTPMethods:

    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            self.response(status_code, 'Resource not found. Check the URL.')
        elif status_code == 405:
            self.response(
                status_code, 'This request is not allowed in this resource. Check your verb (GET,POST,PUT and DELETE)')
        else:
            self.response(
                status_code, 'Request results is an error with the code: %d' % (status_code))

    def response(self, code, message="", data=None, headers=None):
        output_response = {'status': None, 'message': message}
        if data:
            output_response['data'] = data
        if code < 300:
            output_response['status'] = 'success'
        elif code >= 300 and code < 400:
            output_response['status'] = 'redirect'
        elif code >= 400 and code < 500:
            output_response['status'] = 'error'
        else:
            output_response['status'] = 'fail'
        if headers and isinstance(headers, dict):
            for k, v in headers.items():
                self.add_header(k, v)
        self.set_status(code)
        self.write(self.json_encode(output_response))
        self.finish()

    @asynchronous
    @engine
    def api(self, url, method, body=None, headers=None, auth_username=None, auth_password=None, callback=None):
        AsyncHTTPClient.configure(
            "tornado.curl_httpclient.CurlAsyncHTTPClient")
        http_client = AsyncHTTPClient()
        dictheaders = {"content-type": "application/json"}
        if headers:
            for k, v in headers.items():
                dictheaders[k] = v
        h = HTTPHeaders(dictheaders)
        params = {
            'headers': h,
            'url': url,
            'method': method,
            'request_timeout': 720,
            'validate_cert': False}
        if method in ['POST', 'PUT']:
            params['body'] = body
        if auth_username:
            params['auth_username'] = auth_username
            params['auth_password'] = auth_password
        request = HTTPRequest(**params)
        try:
            response = yield http_client.fetch(request)
        except HTTPError as e:
            info('HTTTP error returned... ')
            info(str(e))
            if e.response:
                info('URL: ' + str(e.response.effective_url))
                info('Reason: ' + str(e.response.reason))
                info('Body: ' + str(e.response.body))
                response = e.response
            else:
                response = e
        except Exception as e:
            # Other errors are possible, such as IOError.
            info("Other Errors: " + str(e))
            response = e
        callback(response)

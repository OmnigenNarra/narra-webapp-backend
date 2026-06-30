#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Fake SendGrid server
'''

import os
from http import HTTPStatus
from http.server import CGIHTTPRequestHandler
from socketserver import TCPServer


class RequestHandler(CGIHTTPRequestHandler):
    '''Request handler class
    '''
    def do_POST(self):
        '''POST request handler method
        '''
        if self.path.startswith('/accepted/'):
            self.send_response(HTTPStatus.ACCEPTED)
        elif self.path.startswith('/acquired/'):
            self.send_response(HTTPStatus.OK)
        elif self.path.startswith('/http_error/'):
            self.send_response(HTTPStatus.UNAUTHORIZED)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)

        body_msg = b'{}'
        self.send_header('Content-Length', str(len(body_msg)))
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body_msg)


def main():
    '''Main method
    '''
    host = os.environ.get('FAKE_SENDGRID_SRV_HOST', '')
    port = int(os.environ.get('FAKE_SENDGRID_SRV_PORT', 8025))
    with TCPServer((host, port), RequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == '__main__':
    main()

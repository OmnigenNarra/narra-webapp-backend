# -*- coding: utf-8 -*-

'''App main start module
'''

import mimetypes
from aiohttp import web
from aiohttp_wsgi import WSGIHandler

from .wsgi import application


mimetypes.encodings_map['.br'] = 'brotli'


def make_aiohttp_app(app):
    '''Creates aiohttp app
    '''
    wsgi_handler = WSGIHandler(app)
    aioapp = web.Application()
    aioapp.router.add_route('*', '/{path_info:.*}', wsgi_handler)

    return aioapp


APP = make_aiohttp_app(application)

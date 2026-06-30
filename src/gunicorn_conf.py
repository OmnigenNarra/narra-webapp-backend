# -*- coding: utf-8 -*-

'''Gunicorn config (module)
'''

def when_ready(_):
    '''Ready handler
        bin/start-nginx waits for /tmp/app-initialized to be created before
        binding to a port: https://github.com/beanieboi/nginx-buildpack/
    '''
    open('/tmp/app-initialized', 'w').close()

bind = 'unix:///tmp/nginx.socket'

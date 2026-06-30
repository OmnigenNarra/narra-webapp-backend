# -*- coding: utf-8 -*-

'''Apps module
'''

from django.apps import AppConfig


class ApiConfig(AppConfig):
    '''API app config class
    '''
    name = 'narra_backend.api'
    verbose_name = 'API'

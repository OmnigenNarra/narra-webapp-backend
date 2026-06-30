#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Management module
'''

import os

from django.core.management import execute_from_command_line


def main(argv):
    '''Main method
    '''
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'narra_backend.settings')
    execute_from_command_line(argv)


if __name__ == '__main__':
    main(os.sys.argv)

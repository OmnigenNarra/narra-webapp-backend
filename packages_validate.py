#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Packages validation script
'''

import json
import sys


def main():
    '''Main method
    '''
    import django
    django.setup()

    from narra_backend.api.utils.packages import transform_validate_package

    for fpath in sys.argv[1:]:
        package_dc = json.load(open(fpath, 'rb'))
        _, error = transform_validate_package(package_dc)
        if error:
            print('T:', fpath, '-- FAIL:', error)
            continue

        print('T:', fpath, '-- OK')


if __name__ == '__main__':
    main()

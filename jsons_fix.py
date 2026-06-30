#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''JSONs fix script
'''

import json
import os


def main():
    '''Main method
    '''
    for root, _, files in os.walk('.'):
        for fname in files:
            if fname.endswith('.json'):
                fpath = os.path.join(root, fname)
                print('fixing:', fpath)
                json.dump(
                    json.load(open(fpath, 'rb')), open(fpath, 'w'),
                    sort_keys=True, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()

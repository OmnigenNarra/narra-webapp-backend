# -*- coding: utf-8 -*-

'''Tests module
'''

import sys
import random

from narra_backend.manage import main


def test_manage_main_empty_argv():
    '''Tests manage.main with empty (!) argv
    '''
    exc_raised = None
    try:
        main([])
    except SystemExit as exc:
        exc_raised = exc

    assert isinstance(exc_raised, SystemExit)
    assert exc_raised.code == 1


def test_manage_main_without_args():
    '''Tests manage.main without args (arvg[0] is set)
    '''
    main([sys.argv[0]])


def test_manage_main_bad_command():
    '''Tests manage.main with non-existent command
    '''
    exc_raised = None
    fake_cmd = 'fake_command_' + str(random.randint(1e5, 1e6))
    try:
        main([sys.argv[0], fake_cmd])
    except SystemExit as exc:
        exc_raised = exc

    assert isinstance(exc_raised, SystemExit)
    assert exc_raised.code == 1

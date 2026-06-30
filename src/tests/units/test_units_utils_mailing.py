# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import os
import random
import urllib
from uuid import uuid4

import pytest

from django.conf import settings
from django.core.mail import EmailMessage

from narra_backend.units.utils.mailing import (
    prepare_sg_msg_obj,
    Mailer,
    SendGridEmailBackend,
)


FAKE_SENDGRID_SRV = \
    'http://' + \
    os.environ.get('FAKE_SENDGRID_SRV_HOST', 'localhost') + ':' + \
    os.environ.get('FAKE_SENDGRID_SRV_PORT', '8025')


def test_prepare_sg_msg_obj_full_featured():
    '''Tests prepare_sg_msg_obj method - full-featured message
    '''
    user_name = 'user' + str(random.randint(1e5, 1e6))
    user_email = 'user%s@example.com' % random.randint(1e5, 1e6)
    tpl_id = 'tpl_' + str(random.randint(1e5, 1e6))
    tpl_uid = str(uuid4())
    categories = [tpl_id]

    orig_settings = copy.deepcopy(settings.SENDGRID['TEMPLATES'])

    settings.SENDGRID['TEMPLATES'][tpl_id] = {
        'tpl': tpl_uid,
        'cats': categories,
    }

    substs_key = 'key_' + str(random.randint(1e5, 1e6))
    substs_val = 'val_' + str(random.randint(1e5, 1e6))
    substs_dc = {
        substs_key: substs_val,
    }

    bcc_email = 'bcc-user%s@example.com' % random.randint(1e5, 1e6)

    kwargs = {
        'bcc': [bcc_email],
        'attachments': [(
            'file_%s.dat' % random.randint(1e5, 1e6),
            bytes(str(random.randint(1e5, 1e6)), encoding='utf-8'),
            'application/vnd.narra.v%s' % random.randint(1e5, 1e6))],
    }

    mail = prepare_sg_msg_obj(
        user_name, user_email, tpl_id, substs_dc, **kwargs)

    settings.SENDGRID['TEMPLATES'] = orig_settings

    assert mail.attachments

    content_id = mail.attachments[0].content_id.content_id

    assert mail.get() == {
        'attachments': [
            {
                'content_id': content_id,
                'disposition': 'attachment',
            },
        ],
        'categories': categories,
        'content': [
            {
                'type': 'text/html',
                'value': ' '
            },
        ],
        'from': {
            'email': settings.DEFAULT_FROM_EMAIL,
            'name': settings.DEFAULT_FROM_NAME,
        },
        'personalizations': [
            {
                'bcc': [
                    {
                        'email': bcc_email,
                    },
                ],
                'dynamic_template_data': {
                    substs_key: substs_val,
                },
                'to': [
                    {
                        'email': user_email,
                        'name': user_name,
                    },
                ],
            },
        ],
        'reply_to': {
            'email': settings.DEFAULT_REPLY_EMAIL,
        },
        'subject': ' ',
        'template_id': tpl_uid,
    }


def test_mailer_send_plain_text_mail():
    '''Tests Mailer class - send_plain_text_mail method
    '''
    user_email = 'user%s@example.com' % random.randint(1e5, 1e6)
    message = 'message_' + str(random.randint(1e5, 1e6))
    bcc_email = 'bcc-user%s@example.com' % random.randint(1e5, 1e6)

    result = Mailer.send_plain_text_mail([user_email], message, [bcc_email])

    assert result == [1]


def test_mailer_send_plain_html_mail():
    '''Tests Mailer class - send_plain_html_mail method
    '''
    user_email = 'user%s@example.com' % random.randint(1e5, 1e6)
    message = 'message_' + str(random.randint(1e5, 1e6))
    bcc_email = 'bcc-user%s@example.com' % random.randint(1e5, 1e6)

    result = Mailer.send_plain_html_mail([user_email], message, [bcc_email])

    assert result == [1]


def test_mailer_send_passwd_reset_email():
    '''Tests Mailer class - send_passwd_reset_email method
    '''
    user_name = 'user' + str(random.randint(1e5, 1e6))
    user_email = 'user%s@example.com' % random.randint(1e5, 1e6)
    url = 'https://%s.narra.software/%s' % (
        random.randint(1e5, 1e6), random.randint(1e5, 1e6))

    result = Mailer.send_passwd_reset_email(user_email, user_name, url)

    assert result == 1


def test_mailer_send_generic_email():
    '''Tests Mailer class - send_generic_email method
    '''
    tpl_id = 'tpl_' + str(random.randint(1e5, 1e6))
    tpl_uid = str(uuid4())
    categories = [tpl_id]

    orig_settings = copy.deepcopy(settings.SENDGRID['TEMPLATES'])

    settings.SENDGRID['TEMPLATES'][tpl_id] = {
        'tpl': tpl_uid,
        'cats': categories,
    }

    to_name = 'user' + str(random.randint(1e5, 1e6))
    to_email = 'user%s@example.com' % random.randint(1e5, 1e6)

    substs_key = 'key_' + str(random.randint(1e5, 1e6))
    substs_val = 'val_' + str(random.randint(1e5, 1e6))
    substs_dc = {
        substs_key: substs_val,
    }

    bcc_email = 'bcc-user%s@example.com' % random.randint(1e5, 1e6)

    kwargs = {
        'bcc': [bcc_email],
        'attachments': [(
            'file_%s.dat' % random.randint(1e5, 1e6),
            bytes(str(random.randint(1e5, 1e6)), encoding='utf-8'),
            'application/vnd.narra.v%s' % random.randint(1e5, 1e6))],
    }

    result = Mailer.send_generic_email(
        tpl_id, to_name, to_email, substs_dc, **kwargs)

    settings.SENDGRID['TEMPLATES'] = orig_settings

    assert result == 1


def test_sendgridemailbackend_send_messages_no_messages():
    '''Tests SendGridEmailBackend class - send_messages method, no messages
    '''
    backend = SendGridEmailBackend(False)

    result = backend.send_messages([])

    assert result == 0


def check_missing_sendgrid_fake_server():
    '''Checks for missing SendGrid fake server
    '''
    if not FAKE_SENDGRID_SRV:
        return True

    try:
        urllib.request.urlopen(FAKE_SENDGRID_SRV, data=None, timeout=1)

        return False
    except urllib.error.URLError:
        pass

    return True


@pytest.mark.skipif(
    check_missing_sendgrid_fake_server(), reason='no SendGrid fake server')
def test_sendgridemailbackend_send_messages_py_http_cli_error():
    '''Tests SendGridEmailBackend class - send_messages method,
        python_http_client error
    '''
    user_name = 'User #' + str(random.randint(1e5, 1e6))
    to_email = 'user%s@example.com' % random.randint(1e5, 1e6)

    tpl_id = 'tpl_' + str(random.randint(1e5, 1e6))
    tpl_uid = str(uuid4())
    categories = [tpl_id]

    orig_settings = copy.deepcopy(settings.SENDGRID['TEMPLATES'])

    settings.SENDGRID['TEMPLATES'][tpl_id] = {
        'tpl': tpl_uid,
        'cats': categories,
    }

    backend = SendGridEmailBackend(
        False, host=FAKE_SENDGRID_SRV.replace('http://', 'https://') + '/')

    email = EmailMessage(to=[to_email])
    email.sg_msg_obj = prepare_sg_msg_obj(user_name, to_email, tpl_id, {})

    result = backend.send_messages([email])

    settings.SENDGRID['TEMPLATES'] = orig_settings

    assert result == 0


@pytest.mark.skipif(
    check_missing_sendgrid_fake_server(), reason='no SendGrid fake server')
def test_sendgridemailbackend_send_messages_mail_not_accepted():
    '''Tests SendGridEmailBackend class - send_messages method,
        mail not accepted
    '''
    user_name1 = 'User #' + str(random.randint(1e5, 1e6))
    user_name2 = user_name1
    while user_name2 == user_name1:
        user_name2 = 'User #' + str(random.randint(1e5, 1e6))

    to_email1 = 'user%s@example.com' % random.randint(1e5, 1e6)
    to_email2 = to_email1
    while to_email2 == to_email1:
        to_email2 = 'from%s@example.com' % random.randint(1e5, 1e6)

    tpl_id = 'tpl_' + str(random.randint(1e5, 1e6))
    tpl_uid = str(uuid4())
    categories = [tpl_id]

    orig_settings = copy.deepcopy(settings.SENDGRID['TEMPLATES'])

    settings.SENDGRID['TEMPLATES'][tpl_id] = {
        'tpl': tpl_uid,
        'cats': categories,
    }

    backend = SendGridEmailBackend(False, host=FAKE_SENDGRID_SRV + '/acquired')

    email1 = EmailMessage(to=[to_email1])
    email1.sg_msg_obj = prepare_sg_msg_obj(user_name1, to_email1, tpl_id, {})
    email2 = EmailMessage(to=[to_email2])
    email2.sg_msg_obj = prepare_sg_msg_obj(user_name2, to_email2, tpl_id, {})

    result = backend.send_messages([email1, email2])

    settings.SENDGRID['TEMPLATES'] = orig_settings

    assert result == 2


@pytest.mark.skipif(
    check_missing_sendgrid_fake_server(), reason='no SendGrid fake server')
def test_sendgridemailbackend_send_messages_mail_accepted():
    '''Tests SendGridEmailBackend class - send_messages method,
        mail accepted
    '''
    user_name1 = 'User #' + str(random.randint(1e5, 1e6))
    user_name2 = user_name1
    while user_name2 == user_name1:
        user_name2 = 'User #' + str(random.randint(1e5, 1e6))

    to_email1 = 'user%s@example.com' % random.randint(1e5, 1e6)
    to_email2 = to_email1
    while to_email2 == to_email1:
        to_email2 = 'from%s@example.com' % random.randint(1e5, 1e6)

    tpl_id = 'tpl_' + str(random.randint(1e5, 1e6))
    tpl_uid = str(uuid4())
    categories = [tpl_id]

    orig_settings = copy.deepcopy(settings.SENDGRID['TEMPLATES'])

    settings.SENDGRID['TEMPLATES'][tpl_id] = {
        'tpl': tpl_uid,
        'cats': categories,
    }

    backend = SendGridEmailBackend(False, host=FAKE_SENDGRID_SRV + '/accepted')

    email1 = EmailMessage(to=[to_email1])
    email1.sg_msg_obj = prepare_sg_msg_obj(user_name1, to_email1, tpl_id, {})
    email2 = EmailMessage(to=[to_email2])
    email2.sg_msg_obj = prepare_sg_msg_obj(user_name2, to_email2, tpl_id, {})

    result = backend.send_messages([email1, email2])

    settings.SENDGRID['TEMPLATES'] = orig_settings

    assert result == 2

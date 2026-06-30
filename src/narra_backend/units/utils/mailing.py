# -*- coding: utf-8 -*-

'''Mailing backend module
'''

import copy
import logging
import socket
import threading
import urllib.request as urllib
from base64 import b64encode
from uuid import uuid4

import python_http_client
from rest_framework import status

from django.conf import settings
from django.core.mail import EmailMessage

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Bcc,
    Category,
    Email,
    From,
    Mail,
    To,
)


LOG = logging.getLogger(__name__)


def prepare_sg_msg_obj(user_name, user_email, tpl_id, substs_dc, **kwargs):
    '''Prepares SendGrid message object
    '''
    mail = Mail(subject=' ', html_content=' ')
    mail.to = To(user_email, user_name)
    mail.from_email = From(
        settings.DEFAULT_FROM_EMAIL, settings.DEFAULT_FROM_NAME)
    mail.reply_to = Email(email=settings.DEFAULT_REPLY_EMAIL)
    bccs = kwargs.get('bcc') or []
    if bccs:
        mail.bcc = [Bcc(bcc) for bcc in bccs]

    mail.template_id = settings.SENDGRID['TEMPLATES'][tpl_id]['tpl']
    mail.dynamic_template_data = copy.deepcopy(substs_dc)
    mail.category = [
        Category(cat) for cat in settings.SENDGRID[
            'TEMPLATES'][tpl_id]['cats']]

    attachments = kwargs.get('attachments') or []
    for filename, content, mimetype in attachments:
        att = Attachment()
        att.content = b64encode(content).decode()
        att.type = mimetype
        att.filename = filename
        att.disposition = 'attachment'
        att.content_id = str(uuid4())
        mail.add_attachment(att)

    return mail


class Mailer:
    '''Mailer helper class
    '''
    @staticmethod
    def send_plain_text_mail(emails, message, bcc=None):
        '''Sends plain text mail
        '''
        results = []
        email = EmailMessage(to=emails)
        for user_email in emails:
            email.sg_msg_obj = prepare_sg_msg_obj(
                '', user_email, 'plain_text', {
                    'text_body': message,
                }, bcc=bcc)
            results.append(email.send(fail_silently=False))

        return results

    @staticmethod
    def send_plain_html_mail(emails, message, bcc=None):
        '''Sends plain HTML mail
        '''
        results = []
        email = EmailMessage(to=emails)
        for user_email in emails:
            email.sg_msg_obj = prepare_sg_msg_obj(
                '', user_email, 'plain_html', {
                    'html_body': message,
                }, bcc=bcc)
            results.append(email.send(fail_silently=False))

        return results

    @staticmethod
    def send_passwd_reset_email(user_email, user_name, url):
        '''Sends password reset email
        '''
        return Mailer.send_generic_email(
            'passwd_reset_mail', user_name, user_email, substs_dc={
                'user_name': user_name,
                'passwd_reset_url': url,
            })

    @staticmethod
    def send_generic_email(
            template, to_name, to_email, substs_dc=None, **kwargs):
        '''Sends generic email
        '''
        email = EmailMessage(to=[to_email])
        email.sg_msg_obj = prepare_sg_msg_obj(
            to_name, to_email, template, substs_dc or {}, **kwargs)
        return email.send(fail_silently=False)


class SendGridEmailBackend:
    '''SendGrid mail sending backend
    '''
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently
        self.sg_cli = SendGridAPIClient(settings.SENDGRID['API_KEY'], **kwargs)
        self._lock = threading.RLock()

    def send_messages(self, email_messages):
        '''Sends one or more Mail objects and returns the number of
            email messages sent
        '''
        if not email_messages:
            return 0

        with self._lock:
            num_sent = 0
            for message in email_messages:
                if self._send(message):
                    num_sent += 1

        return num_sent

    def _send(self, email_message):
        '''A helper method that does the actual sending
        '''
        log_msg = repr(email_message.sg_msg_obj.get())
        try:
            response = self.sg_cli.send(email_message.sg_msg_obj)
            LOG.info('mail req sent: %s', log_msg)
            if response.status_code != status.HTTP_202_ACCEPTED:
                LOG.warning(
                    'E%s (%s) @ %s', response.status_code, repr(response.body),
                    log_msg)
        except urllib.HTTPError as exc:
            LOG.error('%s (%s) @ %s', repr(exc), exc.read(), log_msg)
            return False
        except (
                python_http_client.exceptions.HTTPError, socket.error,
                socket.timeout) as exc:
            LOG.error('%s @ %s', repr(exc), log_msg)
            return False

        return True

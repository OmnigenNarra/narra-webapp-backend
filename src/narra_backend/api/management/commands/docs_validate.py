#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Documentation validation command
'''

import io
import json
import logging
import os
import random
import re
from collections import OrderedDict

import yaml
from django_extensions.management.commands import show_urls
from jsonschema import (
    FormatError,
    RefResolutionError,
    SchemaError,
    ValidationError,
    validate as jsonschema_validate,
)
from requests import Request, Session
from rest_framework import status
from rest_framework.authtoken.models import Token as DRFToken

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from narra_backend.api.models import (
    Package,
    Release,
    ReleaseUID,
)
from narra_backend.units.models import (
    Member,
    MemberCode,
    Organization,
    Team,
    TeamMember,
    Token,
)


LOG = logging.getLogger(__name__)

RAML_EXT_RE = re.compile(r'^.+?\.(raml|yaml|yml)$', re.I)
BASE_URL = 'http://127.0.0.1:8000'
BASE_URI = '/api/{version}'
HTTP_METHODS = ['get', 'post', 'put', 'patch', 'delete']
BLACKLISTED_URIS = [
    '/admin/',
    '/media/',
]
DJANGO_ROUTE_VAR_RE = re.compile(r'<(:?[a-z]+:)?([_a-z]+)>')


class NullWriter(io.BytesIO):
    '''Null writer class
    '''
    def write(self, _):
        pass


# based on: https://higgshunter.wordpress.com/2013/06/08/yaml-file-includes/
class RamlLoader(yaml.Loader):
    '''RAML file loader
    '''
    def __init__(self, stream):
        self.root = os.path.split(stream.name)[0]
        super().__init__(stream)
        self.__class__.add_constructor('!include', self.__class__.include)
        self.__class__.add_constructor('!import', self.__class__.include)

    @staticmethod
    def include(instance, node):
        '''`!include` constructor
        '''
        if isinstance(node, yaml.ScalarNode):
            return instance.extract_file(instance.construct_scalar(node))

        if isinstance(node, yaml.SequenceNode):
            result = []
            for filename in instance.construct_sequence(node):
                result += instance.extract_file(filename)

            return result

        if isinstance(node, yaml.MappingNode):
            result = {}
            for key, val in instance.construct_mapping(node).iteritems():
                result[key] = instance.extract_file(val)

            return result

        raise yaml.constructor.ConstructorError(
            'unrecognised node type in !include statement')

    def extract_file(self, filename):
        '''File extraction method
        '''
        filepath = os.path.join(self.root, filename)
        with open(filepath, 'r') as fd_obj:
            return yaml.load(
                fd_obj, Loader=self.__class__) if RAML_EXT_RE.match(
                    filepath) else fd_obj.read()


def pull_raml_uris(raml_spec, base_uri, prefix='', secured_by=None):
    '''Pulls RAML URIs
    '''
    uris = OrderedDict()
    for uri in raml_spec:
        if uri.startswith('/'):
            if set(HTTP_METHODS).intersection(raml_spec[uri].keys()):
                _uri = base_uri + prefix + uri
                if _uri not in uris:
                    uris[_uri] = {}
                for method in HTTP_METHODS:
                    uris[_uri][method] = raml_spec[uri].get(
                        method, OrderedDict())
                    uris[_uri][method].update({
                        'securedBy':
                            raml_spec[uri].get('securedBy') or secured_by})
            uris.update(pull_raml_uris(
                raml_spec[uri], base_uri, prefix + uri, secured_by))

    return uris


def subst_fvar(uri):
    '''Substitutes `.format()` variable
    '''
    return DJANGO_ROUTE_VAR_RE.sub(r'{\2}', uri)


class Requestor:
    '''Stateful HTTP requests class
    '''
    name = 'docs-validator'
    ok_statuses = [
        status.HTTP_200_OK,
        status.HTTP_201_CREATED,
        status.HTTP_202_ACCEPTED,
    ]
    mime = 'application/json'

    def __init__(self, raml_spec, uri):
        self.req_sess = Session()
        self.raml_spec = raml_spec
        self.data = {
            'organization': Organization.objects.get_or_create(
                name=self.name)[0],
            'email': self.name + '@example.com',
        }
        self.data['user'], _ = get_user_model().objects.get_or_create(
            username=self.name, email=self.data['email'],
            is_active=True, is_staff=True, is_superuser=True)

        self.data['passwd'] = Member.objects.make_random_password()
        self.data['member'], _ = Member.objects.get_or_create(
            organization=self.data['organization'], email=self.data['email'],
            is_active=True, org_admin=True)
        self.data['member'].set_passwd(self.data['passwd'])
        self.data['member'].save(update_fields=['passwd'])

        self.data['member_auth_token'], _ = Token.objects.get_or_create(
            member=self.data['member'])
        self.data['user_auth_token'], _ = DRFToken.objects.get_or_create(
            user=self.data['user'])

        self.data['membercode'], _ = MemberCode.objects.get_or_create(
            member=self.data['member'], type=MemberCode.TYPE_PASSWD_RESET)

        self.data['team'], _ = Team.objects.get_or_create(
            organization=self.data['organization'], name=self.name)
        self.data['teammember'], _ = TeamMember.objects.get_or_create(
            team=self.data['team'], member=self.data['member'])

        self.data['package'], _ = Package.objects.get_or_create(
            filename=self.name, author=self.data['member'],
            json_ver=settings.PACKAGE_JSON_VER,
            story_ver=settings.PACKAGE_STORY_VER,
            uasset_ver=settings.PACKAGE_UASSET_VER)

        self.data['release'], _ = Release.objects.get_or_create(
            unreal_ver=str(random.random()),
            release_ver='R#' + str(random.randint(1e5, 1e6)))

        self.data['releaseuid'], _ = ReleaseUID.objects.get_or_create(
            organization=self.data['organization'],
            release=self.data['release'])

        self.uri = uri.format(
            org_id=self.data['organization'].id,
            package_id=self.data['package'].id,
            team_id=self.data['team'].id,
        )

    def send(self, prepped_req, auth_token_type=None):
        '''Sends request
        '''
        if auth_token_type:
            prepped_req.headers['Authorization'] = \
                'Token ' + self.data[auth_token_type].key
        if prepped_req.method != 'get':
            prepped_req.headers['Content-Type'] = self.mime

        return self.req_sess.send(prepped_req, timeout=5.0)

    def expect_e405(self, method, auth_token_type):
        '''Send request - expect HTTP 405 code
        '''
        req = Request(method, BASE_URL + self.uri, data={})
        prepped_req = req.prepare()
        resp = self.send(prepped_req, auth_token_type=auth_token_type)
        if resp.status_code != status.HTTP_405_METHOD_NOT_ALLOWED:
            LOG.warning(
                'Non-E405 response: %s @ %s @ %s',
                resp.content, method, self.uri)

            return

        LOG.info('OK - E405 response %s @ %s', method, self.uri)

    def patch_request_data(self, data, req_data_type):
        '''Patches request data
        '''
        if req_data_type == 'token-auth-req':
            for passwd_field in ['passwd', 'passwd1', 'passwd2']:
                if passwd_field in data:
                    data[passwd_field] = self.data['passwd']
        if req_data_type in [
                'units-teams-update-req', 'units-teams-remove-req']:
            data['id'] = self.data['team'].id
        if req_data_type in [
                'units-teams-add-req', 'units-teams-update-req']:
            data['name'] = data['name'] + ', change #' + str(
                random.randint(1e5, 1e6))
        if req_data_type in [
                'units-team-members-update-req',
                'units-team-members-remove-req']:
            data['id'] = self.data['teammember'].id
        if req_data_type == 'units-team-members-update-req':
            data['email'] = 'change' + str(random.randint(1e5, 1e6)) + \
                '-' + self.data['email']
        if req_data_type == 'units-passwd-reset-act-req':
            data['email'] = self.data['email']
            data['code'] = self.data['membercode'].code
        if req_data_type == 'releaseuids-add-req':
            data['organization'] = self.data['organization'].id
            data['release'] = self.data['release'].id
        if req_data_type == 'releaseuids-update-req':
            data['id'] = self.data['releaseuid'].id

    def expect_e2xx(self, spec, method, auth_token_type):
        '''Send request - expect HTTP 2xx code
        '''
        resp_codes = [
            resp_code for resp_code in spec['responses']
            if resp_code in self.ok_statuses]
        if not resp_codes:
            LOG.error('No 2xx response codes: %s @ %s', spec, self.uri)

            return

        resp_data_type = spec['responses'][resp_codes[0]]['body'][
            self.mime]['type']

        raw_data = None
        if method != 'get':
            req_data_type = spec['body'][self.mime]['type']
            schema = json.loads(self.raml_spec['types'][req_data_type]['type'])
            raw_data = self.raml_spec['types'][req_data_type]['example']
            data = json.loads(raw_data)
            try:
                jsonschema_validate(instance=data, schema=schema)
                LOG.info(
                    'Request validation OK: %s @ %s', method, self.uri)
            except (
                    FormatError, RefResolutionError,
                    SchemaError, ValidationError) as exc:
                LOG.error(
                    'Example schema validation error @ %s: %s',
                    req_data_type, exc)

                return

            self.patch_request_data(data, req_data_type)

            raw_data = bytes(json.dumps(data), encoding='utf-8')

        req = Request(method, BASE_URL + self.uri, data=raw_data)
        prepped_req = req.prepare()
        resp = self.send(prepped_req, auth_token_type=auth_token_type)
        if resp.status_code not in self.ok_statuses:
            LOG.warning(
                'Non-E2xx response: %s @ %s @ %s @ %s',
                resp.status_code, resp.content, method, self.uri)

            return

        LOG.info(
            'OK - E2xx response: %s @ %s', resp.status_code, self.uri)

        schema = json.loads(self.raml_spec['types'][resp_data_type]['type'])
        data = json.loads(self.raml_spec['types'][resp_data_type]['example'])
        try:
            jsonschema_validate(instance=data, schema=schema)
            LOG.info(
                'Documentation validation OK: %s @ %s', method, self.uri)
        except (
                FormatError, RefResolutionError,
                SchemaError, ValidationError) as exc:
            LOG.error(
                'Documentation schema validation error @ %s: %s',
                resp_data_type, exc)

            return

        try:
            jsonschema_validate(instance=resp.json(), schema=schema)
            LOG.info(
                'Response validation OK: %s @ %s', method, self.uri)
        except (
                FormatError, RefResolutionError,
                SchemaError, ValidationError) as exc:
            LOG.error(
                'Response schema validation error @ %s: %s',
                resp_data_type, exc)

            return


def probe_uri(raml_spec, raml_uris, uri):
    '''Probes URI
    '''
    LOG.info('Testing URI: %s', uri)
    requestor = Requestor(raml_spec, uri)
    for method, spec in raml_uris[uri].items():
        auth_token_type = spec.get('securedBy')[0]
        if list(spec.keys()) == ['securedBy']:
            requestor.expect_e405(method, auth_token_type)
        else:
            requestor.expect_e2xx(spec, method, auth_token_type)


class Command(BaseCommand):
    '''Main task class
    '''
    help = 'Documentation validation task'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-r', '--raml-file',
            dest='raml_file',
            type=str,
            required=True,
            help='RAML file')

    def handle(self, *_, **options):
        raml_spec = yaml.load(
            open(options['raml_file'], 'rb'), Loader=RamlLoader)

        base_uri = BASE_URI.format(version=raml_spec['version'])
        raml_uris = pull_raml_uris(
            raml_spec, base_uri, prefix='',
            secured_by=raml_spec.get('securedBy'))

        show_urls_cmd = show_urls.Command()
        show_urls_cmd.stdout = NullWriter()
        django_pats = json.loads(call_command(
            show_urls_cmd, verbosity=options.get('verbosity'), format='json'))

        django_uris = [subst_fvar(pat['url']) for pat in filter(
            lambda pat: not any(
                pat['url'].startswith(uri) for uri in BLACKLISTED_URIS),
            django_pats)]

        diff = set(django_uris).symmetric_difference(raml_uris)
        if diff:
            LOG.warning('URIs diff: %s', diff)

        for uri in django_uris:
            probe_uri(raml_spec, raml_uris, uri)

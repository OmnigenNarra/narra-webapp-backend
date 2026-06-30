# -*- coding: utf-8 -*-

'''Django settings module
'''

import copy
import glob
import json
import os
import urllib.parse
from collections import OrderedDict
from functools import cmp_to_key

import dj_database_url
from semver import (
    compare as semver_compare,
    parse_version_info,
)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


AUTHS_DIR = os.environ.get('AUTHS_DIR', BASE_DIR + '/auths')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    with open(AUTHS_DIR + '/secret_key.dat', 'rb') as fd_obj:
        SECRET_KEY = str(fd_obj.read(), encoding='latin-1')


REDIS_URL = os.environ.get('REDIS_URL', '')
REDIS_PASSWD_ENV = os.environ.get('REDIS_PASSWD')
REDIS_PASSWD_URL = None
if REDIS_URL:
    _PARTS = urllib.parse.urlparse(REDIS_URL)
    _NETLOC_PTS = _PARTS[1].rsplit('@', 1)
    REDIS_PASSWD_URL = _NETLOC_PTS[0].split(':', 1)[0]

REDIS_PASSWD = REDIS_PASSWD_URL
if REDIS_PASSWD_ENV and not REDIS_PASSWD_URL:
    REDIS_PASSWD = REDIS_PASSWD_ENV

if REDIS_URL and REDIS_PASSWD and not REDIS_PASSWD_URL:
    _PARTS = urllib.parse.urlparse(REDIS_URL)
    _NETLOC_PTS = _PARTS[1].rsplit('@', 1)
    REDIS_URL = urllib.parse.urlunparse((
        _PARTS[0],
        ':' + REDIS_PASSWD + '@' + _NETLOC_PTS[1],
        _PARTS[2],
        _PARTS[3],
        _PARTS[4],
        _PARTS[5]))


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False


ALLOWED_HOSTS = ['*']


APPEND_SLASH = False


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'rest_framework',
    'rest_framework.authtoken',
    'narra_backend.api.apps.ApiConfig',
    'narra_backend.units.apps.UnitsConfig',
]
try:
    import django_extensions
    INSTALLED_APPS.append('django_extensions')
except (ModuleNotFoundError, ImportError):
    pass

MIDDLEWARE = [
    'narra_backend.api.utils.views.StaticAuthMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SITE_ID = 1

INTERNAL_IPS = [
    '127.0.0.1',
]

ROOT_URLCONF = 'narra_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'narra_backend', 'templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]


WSGI_APPLICATION = 'narra_backend.wsgi.application'


if os.getenv('DATABASE_URLS_SPLIT', None):
    DATABASES = {
        'narra_u': dj_database_url.config(
            env='DATABASE_URL_U'),
        'narra_a': dj_database_url.config(
            env='DATABASE_URL_A'),
    }
elif os.getenv('DATABASE_URL', None):
    DATABASES = {
        'narra_u': dj_database_url.config(),
    }
    DATABASES['narra_a'] = DATABASES['narra_u']
    POSTGRES_PASSWORD_FILE = os.getenv('POSTGRES_PASSWORD_FILE', None)
    if POSTGRES_PASSWORD_FILE:
        with open(POSTGRES_PASSWORD_FILE, 'rb') as fd_obj:
            POSTGRES_PASSWORD = str(fd_obj.read(), encoding='latin-1').strip()
            for db_id in DATABASES:
                DATABASES[db_id]['PASSWORD'] = POSTGRES_PASSWORD
else:
    DATABASES = {
        'narra_u': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'narra.sqlite3'),
        },
    }
    DATABASES['narra_a'] = DATABASES['narra_u']

DATABASES['default'] = DATABASES['narra_u']


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.' + name,
        'OPTIONS': {
            'min_length': 6} if name == 'MinimumLengthValidator' else {},
    } for name in [
        'UserAttributeSimilarityValidator',
        'MinimumLengthValidator',
        'CommonPasswordValidator',
        'NumericPasswordValidator']
]


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(name)s %(levelname)s %(module)s:'
                      '%(lineno)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'stderr': {
            'level': 'NOTSET' if DEBUG else 'INFO',
            'formatter': 'verbose',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stderr',
        },
    },
    'root': {
        'handlers': ['stderr'],
        'level': 'NOTSET' if DEBUG else 'INFO',
        'propagate': False,
    },
    'loggers': {
    }
}
# django "catch all" and core loggers
for logger in [
        '', 'root', 'django', 'django.request', 'django.db.backends',
        'django.security']:
    LOGGING['loggers'][logger] = copy.deepcopy(LOGGING['root'])


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = False

USE_L10N = False

USE_TZ = True

DATETIME_FORMAT = 'Y-m-d H:i:s e'
DATE_FMT = '%Y-%m-%d'
TIME_FMT = '%H:%M:%S'
DT_FMT = 'iso-8601'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'narra_backend', 'static'),
]
STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('STATIC_ROOT') or os.path.join(BASE_DIR, 'static')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'


MEDIA_ROOT = os.environ.get('MEDIA_ROOT') or os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


CSRF_FAILURE_VIEW = 'narra_backend.api.utils.views.csrf_failure_view'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    # 'DEFAULT_CONTENT_NEGOTIATION_CLASS':
    #     'narra_backend.api.utils.views.ForceJSONClientContentNegotiation',
    'DEFAULT_FILTER_BACKENDS': None,
    'PAGE_SIZE': None,
    'DATETIME_FORMAT': DT_FMT,
    'DATETIME_INPUT_FORMATS': [DT_FMT],
    'DATE_FORMAT': DATE_FMT,
    'DATE_INPUT_FORMATS': [DATE_FMT],
    'TIME_FORMAT': TIME_FMT,
    'TIME_INPUT_FORMATS': [TIME_FMT],
    'UNICODE_JSON': False,
    'COMPACT_JSON': True,
    'STRICT_JSON': True,
    'COERCE_DECIMAL_TO_STRING': True,
}


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache' if REDIS_URL else
                   'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': REDIS_URL if REDIS_URL else 'narra_backend',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True
            },
        },
    },
}


DJANGO_REDIS_IGNORE_EXCEPTIONS = True
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True


AUTHENTICATION_BACKENDS = [
    'narra_backend.units.authentication.MemberAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]


SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


EMAIL_BACKEND = 'narra_backend.units.utils.mailing.SendGridEmailBackend'
SENDGRID = {
    'API_KEY': os.environ.get('SENDGRID_API_KEY') or '...',
    'SENDER': 'support',
    'DOMAIN': 'narra.software',
    'TEMPLATES': {
        'plain_text': {
            'tpl': 'd-a855600b2303444da76045b4d934cafa',
            'cats': [
                'plain text',
                'EN',
            ],
        },
        'plain_html': {
            'tpl': 'd-85043e648e564a42b0ebcd06205d04a4',
            'cats': [
                'plain html',
                'EN',
            ],
        },
        'new_account_passwd_setup_mail': {
            'tpl': 'd-d75433146da941cdb6e649ff5f4ee7e3',
            'cats': [
                'password setup',
                'EN',
            ],
        },
        'passwd_reset_mail': {
            'tpl': 'd-ef38de7aa04845e797dd968efb77f433',
            'cats': [
                'password reset',
                'EN',
            ],
        },
        'new_plugin_release': {
            'tpl': 'd-1acf1603599340d79671a71618aa0af3',
            'cats': [
                'new plugin release',
                'EN',
            ],
        },
    },
}
DEFAULT_FROM_NAME = 'Narra'
DEFAULT_FROM_EMAIL = DEFAULT_REPLY_EMAIL = SENDGRID['SENDER'] + '@' + \
    SENDGRID['DOMAIN']

MEMBER_PASSWD_RESET_URL_FMT = \
    '/static/units/index.html' + \
    '#/password/reset/email/%(email)s/code/%(code)s'


PACKAGE_JSON_VER_MIN = '4.3.0'
PACKAGE_JSON_VER = '4.6.0'
PACKAGE_STORY_VER = '4.12.0'
PACKAGE_UASSET_VER = '2.2.0'
PACKAGE_VERSIONS = OrderedDict([
    # JSONVersion -> {StoryVersion: ..., UAssetVersion: ...}
    ('4.3.0', {'StoryVersion': '4.11.0', 'UAssetVersion': '17.0.0'}),
    ('4.4.0', {'StoryVersion': '4.11.0', 'UAssetVersion': '1.1.0'}),
    ('4.5.0', {'StoryVersion': '4.12.0', 'UAssetVersion': '2.1.0'}),
    ('4.6.0', {'StoryVersion': '4.12.0', 'UAssetVersion': '2.2.0'}),
])


SCHEMAS_DIR = os.path.join(STATIC_ROOT, 'schemas')
PACKAGE_VALIDATION_SCHEMA_PATH = os.path.join(SCHEMAS_DIR, 'validator.json')
PACKAGE_VALIDATION_SCHEMA = {}
if os.path.exists(PACKAGE_VALIDATION_SCHEMA_PATH):
    with open(PACKAGE_VALIDATION_SCHEMA_PATH, 'rb') as fd_obj:
        PACKAGE_VALIDATION_SCHEMA = json.load(fd_obj)

_SCHEMAS = {}
for fpath in glob.glob(os.path.join(SCHEMAS_DIR, '*.json')):
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'rb') as fd_obj:
        version = os.path.basename(fpath)[:-len('.json')]
        try:
            parse_version_info(version)
            _SCHEMAS[version] = json.load(fd_obj)
        except ValueError:
            pass
PACKAGE_SCHEMAS = OrderedDict()
for version in sorted(_SCHEMAS.keys(), key=cmp_to_key(semver_compare)):
    PACKAGE_SCHEMAS[version] = _SCHEMAS[version]

USE_JSONSCHEMA = bool(os.environ.get('USE_JSONSCHEMA'))


HTTP_AUTHZ = os.environ.get('HTTP_AUTHZ')


AWS_ACCESS_KEY_ID = os.environ.get('CLOUDCUBE_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('CLOUDCUBE_SECRET_ACCESS_KEY')
AWS_S3_ENDPOINT_URL = os.environ.get('CLOUDCUBE_URL')
AWS_AUTO_CREATE_BUCKET = False
AWS_STORAGE_BUCKET_NAME = 'cloud-cube'
AWS_STORAGE_PREFIX = 'narra-media'
if AWS_S3_ENDPOINT_URL:
    _PARTS = urllib.parse.urlparse(AWS_S3_ENDPOINT_URL)
    AWS_S3_ENDPOINT_URL = urllib.parse.urlunparse((
        _PARTS[0],
        _PARTS[1].split('.', 1)[1],
        '',
        '',
        '',
        ''))
    AWS_STORAGE_BUCKET_NAME = _PARTS[1].split('.', 1)[0]
    AWS_STORAGE_PREFIX = _PARTS[2].strip('/') + '/' + AWS_STORAGE_PREFIX

AWS_DEFAULT_ACL = 'public-read'
AWS_BUCKET_ACL = 'private'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
S3_USE_SIGV4 = True
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_ADDRESSING_STYLE = 'virtual'

if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


SENTRY_DSN = os.environ.get('SENTRY_DSN')
try:
    import sentry_sdk
    from sentry_sdk.integrations.aiohttp import AioHttpIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
except ImportError:
    SENTRY_DSN = None

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[
        AioHttpIntegration(),
        DjangoIntegration(),
        RedisIntegration()])

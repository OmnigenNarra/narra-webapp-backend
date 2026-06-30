# -*- coding: utf-8 -*-

'''URLconf module
'''

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views import static


urlpatterns = [
    path(r'api/v1/', include(('narra_backend.api.urls', 'api'))),
    path(r'admin/', admin.site.urls),
]

if not settings.AWS_S3_ENDPOINT_URL:
    urlpatterns += [
        path(
            r'%s<path:path>' % settings.MEDIA_URL.lstrip('/'),
            static.serve, {'document_root': settings.MEDIA_ROOT}),
    ]

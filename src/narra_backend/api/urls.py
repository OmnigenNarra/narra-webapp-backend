# -*- coding: utf-8 -*-

'''URLconf module
'''

from django.urls import include, path

from . import views


urlpatterns = [
    path(
        r'package/<int:package_id>/download',
        views.PackageDownloadView.as_view(),
        name='package-download'),
    path(
        r'package/<int:package_id>', views.PackageView.as_view(),
        name='package'),
    path(
        r'package/<int:package_id>/lock', views.PackageLockView.as_view(),
        name='package-lock'),
    path(
        r'packages', views.PackagesListView.as_view(),
        name='packages-list'),
    path(
        r'package/check', views.CheckPackageView.as_view(),
        name='package-check'),
    path(
        r'package/validate', views.ValidatePackageView.as_view(),
        name='package-validate'),
    path(
        r'package', views.AddPackageView.as_view(),
        name='package-add'),
    path(
        r'token-auth', views.ObtainAuthToken.as_view(),
        name='token-auth'),
    path(r'', include(('narra_backend.units.urls', 'units'))),
    path(
        r'releaseuids',
        views.ReleaseUIDsViewSet.as_view(
            {
                'get': 'list',
                'post': 'create',
                'patch': 'update'}),
        name='releaseuids'),
]

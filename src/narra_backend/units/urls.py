# -*- coding: utf-8 -*-

'''URLconf module
'''

from django.urls import path

from . import views


urlpatterns = [
    path(
        r'org/<int:org_id>/signin',
        views.OrganizationSignInViewSet.as_view({'post': 'create'}),
        name='organization-signin'),
    path(
        r'org/<int:org_id>/teams',
        views.TeamsViewSet.as_view(
            {
                'get': 'list',
                'post': 'create',
                'patch': 'update',
                'delete': 'destroy'}),
        name='teams'),
    path(
        r'org/<int:org_id>/team/<int:team_id>/members',
        views.TeamMembersViewSet.as_view(
            {
                'get': 'list',
                'post': 'create',
                'patch': 'update',
                'delete': 'destroy'}),
        name='team-members'),
    path(
        r'password/reset',
        views.PasswordResetViewSet.as_view(
            {'post': 'create', 'patch': 'update'}),
        name='password-reset'),
]

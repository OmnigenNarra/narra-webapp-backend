# -*- coding: utf-8 -*-

'''Tests module
'''

import random

import pytest

from django.conf import settings
from django.core.signals import setting_changed
from django.db import IntegrityError

from narra_backend.units.models import (
    CustomAbstractUser,
    Member,
    MemberCode,
    Organization,
    OrganizationGroup,
    Team,
    TeamMember,
    Token,
)


def test_organization_class_repr():
    '''Tests Organization model - repr
    '''
    org_id = random.randint(1e5, 1e6)
    org_name = 'Organization #' + str(random.randint(1e5, 1e6))
    org = Organization(id=org_id, name=org_name)

    assert str(org) == '[%s] %s' % (org.id, org.name)


def test_organizationgroup_class_repr():
    '''Tests OrganizationGroup model - repr
    '''
    group_id = random.randint(1e5, 1e6)
    group_name = 'OrganizationGroup #' + str(random.randint(1e5, 1e6))
    group = OrganizationGroup(id=group_id, name=group_name)

    assert str(group) == '[%s] %s' % (group.id, group.name)


def test_customabstractuser_class_repr():
    '''Tests CustomAbstractUser model - repr
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    user = CustomAbstractUser(email=email)

    assert str(user) == email


@pytest.mark.django_db
def test_customabstractuser_member_doubled_email():
    '''Tests CustomAbstractUser / Member model - doubled email
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    try:
        Member.objects.create(email=member.email)

        assert False
    except IntegrityError:
        pass


@pytest.mark.django_db
def test_customabstractuser_member_check_passwd():
    '''Tests CustomAbstractUser / Member model - check_passwd method
    '''
    old_hasher = 'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher'
    settings.PASSWORD_HASHERS.insert(0, old_hasher)
    setting_changed.send(
        sender=getattr(settings, '_wrapped').__class__,
        setting='PASSWORD_HASHERS', value=settings.PASSWORD_HASHERS,
        enter=True)

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(email=email)
    member.set_passwd(passwd)
    member.save()

    settings.PASSWORD_HASHERS.remove(old_hasher)
    settings.PASSWORD_HASHERS.append(old_hasher)
    setting_changed.send(
        sender=getattr(settings, '_wrapped').__class__,
        setting='PASSWORD_HASHERS', value=settings.PASSWORD_HASHERS,
        enter=True)

    passwd_check_res = member.check_passwd(passwd)

    settings.PASSWORD_HASHERS.remove(old_hasher)
    setting_changed.send(
        sender=getattr(settings, '_wrapped').__class__,
        setting='PASSWORD_HASHERS', value=settings.PASSWORD_HASHERS,
        enter=True)

    assert passwd_check_res


def test_customabstractuser_is_anonymous():
    '''Tests CustomAbstractUser model - is_anonymous property
    '''
    user = CustomAbstractUser()

    assert not user.is_anonymous


def test_customabstractuser_is_authenticated():
    '''Tests CustomAbstractUser model - is_authenticated property
    '''
    user = CustomAbstractUser()

    assert user.is_authenticated


def test_member_has_module_perms():
    '''Tests Member model - has_module_perms method
    '''
    module = 'mod_' + str(random.randint(1e5, 1e6))
    member = Member()

    assert not member.has_module_perms(module)


def test_member_repr():
    '''Tests Member model - repr
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member(email=email)

    assert str(member) == email


def test_member_get_username():
    '''Tests Member model - get_username method
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member(email=email)

    assert member.get_username() == email


def test_member_set_password():
    '''Tests Member model - set_password method
    '''
    passwd = Member.objects.make_random_password()
    member = Member()
    member.set_password(passwd)

    assert member.check_passwd(passwd)


def test_member_iter():
    '''Tests Member model - iterator
    '''
    member_id = random.randint(1e5, 1e6)
    member = Member(id=member_id)

    assert dict(member) == {'id': member_id}


def test_membercode_repr():
    '''Tests MemberCode model - repr
    '''
    member_id = random.randint(1e5, 1e6)
    member = Member(id=member_id)
    member_code_type = random.choice(MemberCode.TYPES)[0]
    member_code_code = 'c0d3' * random.randint(5, 10)

    member_code = MemberCode(
        member=member, type=member_code_type, code=member_code_code)

    assert str(member_code) == 'MID=%s T=%s C=%s...' % (
        member_id, member_code_type, member_code_code[:16])


@pytest.mark.django_db
def test_membercode_code_autogen_full_save():
    '''Tests MemberCode model - code autogeneration, full save
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    member_code = MemberCode.objects.create(
        member=member, type=MemberCode.TYPE_ACCOUNT_ACTIV)

    assert member_code.code


@pytest.mark.django_db
def test_membercode_code_autogen_partial_save():
    '''Tests MemberCode model - code autogeneration, partial save
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    member_code = MemberCode.objects.create(
        member=member, type=MemberCode.TYPE_ACCOUNT_ACTIV)

    old_code = member_code.code

    assert old_code

    member_code.code = ''
    member_code.save(update_fields=['created'])
    new_code = member_code.code

    assert new_code
    assert old_code != new_code


def test_token_repr():
    '''Tests Token model - repr
    '''
    token_key = 'k3y' * random.randint(9, 15)

    token = Token(key=token_key)

    assert str(token) == token_key[:32] + '...'


@pytest.mark.django_db
def test_toekn_key_autogen_full_save():
    '''Tests Token model - key autogeneration, full save
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    token = Token.objects.create(member=member)

    assert token.key


def test_teammember_class_repr():
    '''Tests TeamMember model - repr
    '''
    team_id = random.randint(1e5, 1e6)
    team_name = 'Team_' + str(random.randint(1e5, 1e6))
    team = Team(id=team_id, name=team_name)

    member_id = random.randint(1e5, 1e6)
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member(id=member_id, email=email)
    teammember = TeamMember(team=team, member=member)

    assert str(teammember) == 'TID=%s MID=%s' % (team.id, member.id)


@pytest.mark.django_db
def test_teammember_user_is_member_no_members():
    '''Tests TeamMember model - no members test
    '''
    teamname = 'Team_' + str(random.randint(1e5, 1e6))
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    team = Team.objects.create(name=teamname)

    assert not TeamMember.is_member(team, member)


@pytest.mark.django_db
def test_teammember_user_is_member_bad_member():
    '''Tests TeamMember model - user is not member test
    '''
    teamname1 = 'Team_' + str(random.randint(1e5, 1e6))
    teamname2 = teamname1
    while teamname2 == teamname1:
        teamname2 = 'Team_' + str(random.randint(1e5, 1e6))
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)

    member1 = Member.objects.create(email=email1)
    member2 = Member.objects.create(email=email2)
    team1 = Team.objects.create(name=teamname1)
    team2 = Team.objects.create(name=teamname2)
    team1.add_member(member1)
    team2.add_member(member2)

    assert not TeamMember.is_member(team1, member2)
    assert not TeamMember.is_member(team2, member1)


@pytest.mark.django_db
def test_teammember_user_is_member_ok_member():
    '''Tests TeamMember model - user is OK member test
    '''
    teamname = 'Team_' + str(random.randint(1e5, 1e6))
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    team = Team.objects.create(name=teamname)
    team.add_member(member)

    assert TeamMember.is_member(team, member)


def test_team_class_repr():
    '''Tests Team model - repr
    '''
    team_id = random.randint(1e5, 1e6)
    team_name = 'Team_' + str(random.randint(1e5, 1e6))
    team_obj = Team(id=team_id, name=team_name)

    assert str(team_obj) == '[' + str(team_id) + '] ' + team_name


@pytest.mark.django_db
def test_team_user_is_member_no_members():
    '''Tests Team model - no members test
    '''
    teamname = 'Team_' + str(random.randint(1e5, 1e6))
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    team_obj = Team.objects.create(name=teamname)

    assert not team_obj.is_member(member)


@pytest.mark.django_db
def test_team_user_is_member_bad_member():
    '''Tests Team model - user is not member test
    '''
    teamname1 = 'Team_' + str(random.randint(1e5, 1e6))
    teamname2 = teamname1
    while teamname2 == teamname1:
        teamname2 = 'Team_' + str(random.randint(1e5, 1e6))
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)

    member1 = Member.objects.create(email=email1)
    member2 = Member.objects.create(email=email2)
    team1 = Team.objects.create(name=teamname1)
    team2 = Team.objects.create(name=teamname2)
    team1.add_member(member1)
    team2.add_member(member2)

    assert not team1.is_member(member2)
    assert not team2.is_member(member1)


@pytest.mark.django_db
def test_team_user_is_member_ok_member():
    '''Tests Team model - user is OK member test
    '''
    teamname = 'Team_' + str(random.randint(1e5, 1e6))
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    team = Team.objects.create(name=teamname)
    team.add_member(member)

    assert team.is_member(member)

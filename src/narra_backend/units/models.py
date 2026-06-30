# -*- coding: utf-8 -*-

'''Models module
'''

import binascii
import os

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models.deletion import CASCADE
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _u


TOKEN_BITS = 512


class Organization(models.Model):
    '''Organization model class
    '''
    name = models.CharField(
        _u('name'), max_length=256, db_index=True, unique=True)
    ctime = models.DateTimeField(
        _u('creation time'), default=timezone.now)
    members_limit = models.PositiveIntegerField(
        _u('members limit'), null=True, blank=True, default=None)
    organization_groups = models.ManyToManyField(
        'units.OrganizationGroup', blank=True)

    class Meta:
        abstract = False
        verbose_name = _u('Organization')
        verbose_name_plural = _u('Organizations')

    def __str__(self):
        return '[%s] %s' % (self.id, self.name)


class OrganizationGroup(models.Model):
    '''Organization group model class
    '''
    name = models.CharField(
        _u('name'), max_length=256, db_index=True, unique=True)

    class Meta:
        abstract = False
        verbose_name = _u('Organization group')
        verbose_name_plural = _u('Organization groups')

    def __str__(self):
        return '[%s] %s' % (self.id, self.name)


class Team(models.Model):
    '''Team model class
    '''
    organization = models.ForeignKey(
        'units.Organization', null=True, blank=True, on_delete=CASCADE)
    name = models.CharField(
        _u('name'), max_length=128, db_index=True, unique=True)
    ctime = models.DateTimeField(
        _u('creation time'), default=timezone.now)

    class Meta:
        abstract = False
        verbose_name = _u('Team')
        verbose_name_plural = _u('Teams')

    def __str__(self):
        return '[%s] %s' % (self.id, self.name)

    def add_member(self, user):
        '''Checks if user is a team member
        '''
        return TeamMember.objects.get_or_create(team=self, member=user)

    def is_member(self, user):
        '''Checks if user is a team member
        '''
        return TeamMember.is_member(self, user)


class CustomAbstractUser(models.Model):
    '''Custom (abstract) user model class
    '''
    email = models.EmailField(
        _u('email address'), max_length=255, unique=True, db_index=True,
        help_text=_u('<br/><a href="../password/">Password change form</a>'))
    passwd = models.CharField(
        _u('password'), max_length=150)
    passwd_exp = models.DateTimeField(
        _u('password expiration'), blank=True, null=True)
    jtime = models.DateTimeField(
        _u('join time'), default=timezone.now)
    is_active = models.BooleanField(
        _u('active'), default=False)
    last_login = models.DateTimeField(
        _u('last login'), blank=True, null=True)

    # NOTE: for objects manager
    USERNAME_FIELD = 'email'

    class Meta:
        '''Meta class definition
        '''
        abstract = True

    def __str__(self):
        return self.email

    def set_passwd(self, raw_passwd):
        '''Password field setter (scrambler)
        '''
        self.passwd = make_password(raw_passwd)

    def check_passwd(self, passwd):
        '''Password check method
        '''
        def passwd_setter(raw_passwd):
            '''Password field setter (saver)
            '''
            self.set_passwd(raw_passwd)
            self.save(update_fields=['passwd'])

        return check_password(passwd, self.passwd, passwd_setter)

    @property
    def is_anonymous(self):
        '''Always return False
        '''
        return False

    @property
    def is_authenticated(self):
        '''Always return True
        '''
        return True


class MemberManager(BaseUserManager):
    '''Member class objects manager
    '''
    model = 'units.Member'


class Member(CustomAbstractUser):
    '''Member model class
    '''
    organization = models.ForeignKey(
        'units.Organization', null=True, blank=True, on_delete=CASCADE)
    org_admin = models.BooleanField(
        _u('org. admin'), default=False)

    is_staff = False
    objects = MemberManager()

    def __str__(self):
        return self.email

    class Meta:
        abstract = False
        verbose_name = _u('Member')
        verbose_name_plural = _u('Members')

    @classmethod
    def has_module_perms(cls, _):
        '''Tests if user has module permissions
        '''
        return False

    def get_username(self):
        '''Username field getter
        '''
        return self.email

    def set_password(self, raw_passwd):
        '''Password field setter
        '''
        super().set_passwd(raw_passwd)

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        yield ('id', self.id)


class MemberCode(models.Model):
    '''Members' codes class
    '''
    TYPE_ACCOUNT_ACTIV = 'acc_act'
    TYPE_ACCOUNT_REMOVAL = 'acc_rm'
    TYPE_PASSWD_RESET = 'pwd_rst'
    TYPES = [
        (TYPE_ACCOUNT_ACTIV, _u('account activation')),
        (TYPE_ACCOUNT_REMOVAL, _u('account removal')),
        (TYPE_PASSWD_RESET, _u('password reset')),
    ]
    member = models.ForeignKey(
        'units.Member', null=True, blank=True, on_delete=CASCADE)
    type = models.CharField(
        _u('type'), choices=TYPES, db_index=True, max_length=16)
    code = models.CharField(
        _u('code'), db_index=True, max_length=256)
    created = models.DateTimeField(
        _u('created'), default=timezone.now)

    class Meta:
        abstract = False
        verbose_name = _u('Member code')
        verbose_name_plural = _u('Member codes')

    def __str__(self):
        return 'MID=%s T=%s C=%s...' % (
            self.member_id, self.type, self.code[:16])

    @classmethod
    def _generate_key(cls):
        return binascii.hexlify(os.urandom(int(TOKEN_BITS / 8))).decode()

    def save(
            self, force_insert=False, force_update=False, using=None,
            update_fields=None):
        if not self.code:
            self.code = self._generate_key()
            if update_fields and 'code' not in update_fields:
                update_fields = set(['code'] + list(update_fields))
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using,
            update_fields=update_fields)


class TeamMember(models.Model):
    '''Team's member class
    '''
    team = models.ForeignKey(
        'units.Team', null=True, blank=True, on_delete=CASCADE)
    member = models.ForeignKey(
        'units.Member', null=True, blank=True, on_delete=CASCADE)
    jtime = models.DateTimeField(
        _u('join time'), default=timezone.now)

    class Meta:
        abstract = False
        verbose_name = _u('Team\'s member')
        verbose_name_plural = _u('Team\'s members')

    def __str__(self):
        return 'TID=%s MID=%s' % (self.team_id, self.member_id)

    @classmethod
    def is_member(cls, team, member):
        '''Checks if user is a team member
        '''
        return cls.objects.filter(team=team, member=member).exists()


class Token(models.Model):
    '''Authorization token model class
    '''
    key = models.CharField(
        _u('key'), max_length=int(TOKEN_BITS / 4), primary_key=True)
    member = models.OneToOneField('units.Member', on_delete=CASCADE)
    created = models.DateTimeField(
        _u('created'), default=timezone.now)

    class Meta:
        '''Meta class definition
        '''
        abstract = False
        verbose_name = _u('Token')
        verbose_name_plural = _u('Tokens')

    def save(
            self, force_insert=False, force_update=False, using=None,
            update_fields=None):
        if not self.key:
            while not self.key or Token.objects.filter(key=self.key).exists():
                self.key = self._generate_key()
            update_fields = None
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using,
            update_fields=update_fields)

    @classmethod
    def _generate_key(cls):
        return binascii.hexlify(os.urandom(int(TOKEN_BITS / 8))).decode()

    def __str__(self):
        return self.key[:32] + '...'

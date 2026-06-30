# -*- coding: utf-8 -*-

'''Serializers module
'''

from rest_framework import fields, serializers

from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _u

from .models import (
    Member,
    MemberCode,
    Organization,
    Team,
    TeamMember,
    Token,
)


class SignInSerializer(serializers.Serializer):
    '''Sign-in serializer class
    '''
    email = fields.EmailField()
    passwd = fields.CharField(
        write_only=True, style={'input_type': 'password'},
        trim_whitespace=False)
    token = fields.CharField(read_only=True)
    code = fields.CharField(read_only=True)
    passwd_exp = fields.BooleanField(read_only=True)
    jtime = fields.IntegerField(read_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        passwd = attrs.get('passwd')

        user = authenticate(email=email, passwd=passwd, is_active=True)
        if not user:
            raise serializers.ValidationError(
                _u('Unable to log in with provided credentials.'),
                code='authorization')

        if 'extra_auth_params' in self.initial_data:
            extra_test = True
            for key, val in self.initial_data['extra_auth_params'].items():
                extra_test = extra_test and (getattr(user, key) == val)
            if not extra_test:
                raise serializers.ValidationError(
                    _u('Unable to proceed.'),
                    code='authorization')

        attrs['email'] = user.email
        attrs['jtime'] = int(user.jtime.timestamp())
        attrs['token'] = None
        attrs['code'] = None
        attrs['passwd_exp'] = False

        if user.passwd_exp and user.passwd_exp <= timezone.now():
            member_code, _ = MemberCode.objects.get_or_create(
                member=user, type=MemberCode.TYPE_PASSWD_RESET)
            attrs['code'] = member_code.code
            attrs['passwd_exp'] = True
        else:
            token, _ = Token.objects.get_or_create(member=user)
            attrs['token'] = token.key

        return attrs

    def create(self, _):
        return False

    def update(self, instance, _):
        return instance


class OrganizationSerializer(serializers.ModelSerializer):
    '''Organization serializer class
    '''
    class Meta:
        model = Organization
        fields = ['id', 'name']

    def create(self, _):
        return False

    def update(self, instance, _):
        return instance


class TeamSerializer(serializers.ModelSerializer):
    '''Team serializer class
    '''
    organization = fields.IntegerField(write_only=True)

    class Meta:
        model = Team
        fields = ['id', 'organization', 'name', 'ctime']

    def create(self, validated_data):
        return Team.objects.create(
            organization_id=validated_data['organization'],
            name=validated_data['name'])

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.save(update_fields=['name'])

        return instance


class TeamMemberSerializer(serializers.ModelSerializer):
    '''Team member serializer class
    '''
    organization = fields.IntegerField(write_only=True)
    team = fields.IntegerField(write_only=True)
    email = fields.EmailField(source='member')

    class Meta:
        model = TeamMember
        fields = ['id', 'organization', 'team', 'email', 'jtime']

    def validate(self, attrs):
        '''Validates members count
        '''
        org_obj = Organization.objects.get(pk=attrs['organization'])
        if self.context['request'].method == 'POST':
            if org_obj.members_limit is not None and Member.objects.filter(
                    organization=org_obj).count() >= org_obj.members_limit:
                raise serializers.ValidationError(_u('Members limit reached'))

        try:
            member = Member.objects.get(email=attrs['member'])
            if member.organization != org_obj:
                raise serializers.ValidationError(_u('Organization mismatch'))
            if self.context['request'].method == 'PATCH' and \
                    self.initial_data['member_id'] != member.id:
                raise serializers.ValidationError(_u('Email exists'))
        except Member.DoesNotExist:
            pass

        return attrs

    def create(self, validated_data):
        member, _ = Member.objects.get_or_create(
            email=validated_data['member'],
            defaults={
                'passwd_exp': timezone.now(),
                'is_active': True,
                'organization_id': validated_data['organization']})

        team_member = TeamMember.objects.create(
            team_id=validated_data['team'], member=member)

        team_member.email = member.email

        return team_member

    def update(self, instance, validated_data):
        instance.member.email = validated_data.get(
            'member', instance.member.email)
        instance.member.save(update_fields=['email'])

        return instance


class PasswordResetRequestSerializer(serializers.Serializer):
    '''Password reset request serializer
    '''
    email = serializers.EmailField()

    def create(self, _):
        return False

    def update(self, instance, _):
        return instance


class PasswordResetActionSerializer(serializers.Serializer):
    '''Password reset action serializer
    '''
    email = fields.EmailField()
    code = fields.CharField()
    passwd1 = fields.CharField(
        style={'input_type': 'password'}, trim_whitespace=False,
        write_only=True)
    passwd2 = fields.CharField(
        style={'input_type': 'password'}, trim_whitespace=False,
        write_only=True)

    @classmethod
    def validate(cls, attrs):
        '''Validates passwords match
        '''
        if attrs['passwd1'] != attrs['passwd2']:
            raise serializers.ValidationError(_u('Passwords mismatch'))

        return attrs

    def create(self, _):
        return False

    def update(self, instance, _):
        return instance

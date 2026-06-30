# -*- coding: utf-8 -*-

'''Tests module
'''

import random
import string

import pytest

from narra_backend.api.models import (
    ReleaseUID,
)

from narra_backend.api.utils.strings import (
    make_random_text,
    gen_uniq_ident,
)


def test_make_random_text_empty_chars_set():
    '''Tests make_random_text method - empty characters set
    '''
    length = random.randint(1e1, 1e2)
    chars_sets = ''

    try:
        make_random_text(length, chars_sets)

        assert False
    except ZeroDivisionError:
        pass


def test_make_random_text_single_char_set():
    '''Tests make_random_text method - single character set
    '''
    length = random.randint(1e1, 1e2)
    chars_sets = random.choice(string.printable)

    text = make_random_text(length, chars_sets)

    assert text.count(chars_sets) == length


def test_make_random_text_single_type_chars_set():
    '''Tests make_random_text method - single type characters set
    '''
    length = random.randint(1e1, 1e2)
    chars_sets = string.digits

    text = make_random_text(length, chars_sets)

    assert text.isdecimal()


def test_make_random_text_mixed_type_chars_set():
    '''Tests make_random_text method - mixed type characters set
    '''
    length = random.randint(1e1, 1e2)
    chars_sets = string.ascii_letters + string.digits

    text = make_random_text(length, chars_sets)

    assert text.isalnum()


@pytest.mark.django_db
def test_gen_uniq_ident_identity_gen_fn():
    '''Tests gen_uniq_ident method - identity gen_fn
    '''
    gen_fn_vals = ReleaseUID.objects.all().values_list('uid', flat=True)

    gen_fn_val = ''
    while not gen_fn_val or gen_fn_val in gen_fn_vals:
        gen_fn_val = 'UID-' + str(random.randint(1e5, 1e6))

    def gen_fn():
        '''Sample gen_fn function
        '''
        return gen_fn_val

    uniq_ident = gen_uniq_ident(ReleaseUID, 'uid', gen_fn)

    assert uniq_ident not in gen_fn_vals
    assert uniq_ident == gen_fn_val


@pytest.mark.django_db
def test_gen_uniq_ident_multi_pass_gen_fn():
    '''Tests gen_uniq_ident method - multi-pass gen_fn
    '''
    gen_fn_val1 = 'UID-' + str(random.randint(1e5, 1e6))
    gen_fn_val2 = gen_fn_val1
    while gen_fn_val2 == gen_fn_val1:
        gen_fn_val2 = 'UID-' + str(random.randint(1e5, 1e6))

    ReleaseUID.objects.create(uid=gen_fn_val1)

    gen_fn_vals = [gen_fn_val1]

    mul = random.randint(1e1, 1e2)
    gen_fn_gen = (val for val in [gen_fn_val1] * mul + [gen_fn_val2])

    def gen_fn():
        '''Sample gen_fn function
        '''
        return next(gen_fn_gen)

    uniq_ident = gen_uniq_ident(ReleaseUID, 'uid', gen_fn)

    assert uniq_ident not in gen_fn_vals
    assert uniq_ident == gen_fn_val2


@pytest.mark.django_db
def test_gen_uniq_ident_too_long_gen_fn_val():
    '''Tests gen_uniq_ident method - too long gen_fn value
    '''
    attr = 'uid'
    opts = getattr(ReleaseUID, '_meta')
    attr_len = opts.get_field(attr).max_length
    length = 2 * attr_len
    chars_sets = string.ascii_letters + string.digits

    gen_fn_val1 = make_random_text(length, chars_sets)
    gen_fn_val2 = gen_fn_val1
    while gen_fn_val2 == gen_fn_val1:
        gen_fn_val2 = make_random_text(length, chars_sets)

    ReleaseUID.objects.create(uid=gen_fn_val1[:attr_len])

    gen_fn_vals = [
        gen_fn_val1[:attr_len],
        gen_fn_val1,
        gen_fn_val1[:attr_len] + gen_fn_val2[attr_len:],
    ]

    gen_fn_gen = (val for val in gen_fn_vals + [gen_fn_val2])

    def gen_fn():
        '''Sample gen_fn function
        '''
        return next(gen_fn_gen)

    uniq_ident = gen_uniq_ident(ReleaseUID, attr, gen_fn)

    assert uniq_ident not in gen_fn_vals
    assert uniq_ident == gen_fn_val2


@pytest.mark.django_db
def test_gen_uniq_ident_random_pass_gen_fn():
    '''Tests gen_uniq_ident method - random-pass gen_fn
    '''
    gen_fn_vals = ReleaseUID.objects.all().values_list('uid', flat=True)

    def gen_fn():
        '''Sample gen_fn function
        '''
        return make_random_text(
            random.randint(1e2, 1e3),
            string.ascii_letters + string.digits)

    uniq_ident = gen_uniq_ident(ReleaseUID, 'uid', gen_fn)

    assert uniq_ident not in gen_fn_vals

# -*- coding: utf-8 -*-

'''Strings helper module
'''

from random import SystemRandom


SYS_RND = SystemRandom()


def make_random_text(length, chars_sets):
    '''Makes short pseudo-random text from given char sets
    '''
    text = ''
    ch_sets = SYS_RND.sample(chars_sets, len(chars_sets))
    while len(text) < length:
        text += SYS_RND.choice(ch_sets[len(text) % len(ch_sets)])

    return ''.join(SYS_RND.sample(text, length))


def gen_uniq_ident(cls, attr, gen_fn):
    '''Generates unique identifier for to-be-persisted `cls`-class DB object
    '''
    opts = getattr(cls, '_meta')
    attr_len = opts.get_field(attr).max_length
    while True:
        try:
            val = gen_fn()
            query = {attr: val[:attr_len]}
            _ = cls.objects.get(**query)
        except cls.DoesNotExist:
            return val

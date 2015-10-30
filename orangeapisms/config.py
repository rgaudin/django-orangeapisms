#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def build_config(default, user):
    return {
        key: user.get(key, default.get(key, None)) for key in default.keys()
    }

DEFAULT_CONFIG = {
    'handler_module': 'orangeapisms.stub',
    'use_db': True,
    'smsmt_url': 'https://api.sdp.orange.com/smsmessaging/v1',
    'sender_address': '+9912345',
    'sender_name': "API Custom Name",
    'token': None,
    'enable_tester': False,
    'default_sender_name': 'sender_address',
    'send_async': False,
    'celery_app': None,
}

CONFIG = build_config(DEFAULT_CONFIG, settings.ORANGE_API)


def get_config(key, default=None, raw=False):
    if key == 'default_sender_name' and not raw:
        nkey = CONFIG.get(key, True)
        if nkey in CONFIG.keys():
            return get_config(nkey)
    return CONFIG.get(key, default)

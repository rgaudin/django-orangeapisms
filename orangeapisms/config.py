#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import logging
import os
import importlib
import simplejson

from orangeapisms.datetime import encode_datetime, decode_datetime

SETTINGS_FNAME = 'orangeapi.json'
logger = logging.getLogger(__name__)


def build_config(default, user, extra=None):
    if extra is not None:
        user.update(extra)
    return {
        key: user.get(key, default.get(key, None)) for key in default.keys()
    }


def get_settings_folder():
    return os.path.dirname(
        importlib.import_module(os.environ['DJANGO_SETTINGS_MODULE']).__file__)


def get_json_config():
    with open(os.path.join(get_settings_folder(), SETTINGS_FNAME), 'r') as f:
        return simplejson.load(f, object_hook=decode_datetime)

DEFAULT_CONFIG = {
    'handler_module': 'orangeapisms.stub',
    'use_db': True,
    'smsmt_url': 'https://api.orange.com/smsmessaging/v1',
    'oauth_url': 'https://api.orange.com/oauth/v2',
    'sender_address': '+22300000',
    'sender_name': "API Custom Name",
    'client_id': None,
    'client_secret': None,
    'token': None,
    'enable_tester': False,
    'default_sender_name': 'sender_address',
    'send_async': False,
    'celery_module': None,
}

CONFIG = build_config(DEFAULT_CONFIG, get_json_config())


def get_config(key, default=None, raw=False):
    if key == 'default_sender_name' and not raw:
        nkey = CONFIG.get(key, True)
        if nkey in CONFIG.keys():
            return get_config(nkey)
    return CONFIG.get(key, default)


def update_config(extra, save=False):
    CONFIG.update(extra)
    if save:
        with open(os.path.join(get_settings_folder(),
                               SETTINGS_FNAME), 'w') as f:
            simplejson.dump(CONFIG, f, default=encode_datetime, indent=4)

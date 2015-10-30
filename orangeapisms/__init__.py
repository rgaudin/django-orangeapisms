#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

from orangeapisms.config import get_config


def import_path(callable_name, module, fallback=None):
    def do_import(name):
        ''' import a callable from full module.callable name '''
        modname, __, attr = name.rpartition('.')
        if not modname:
            # single module name
            return __import__(attr)
        m = __import__(modname, fromlist=[attr])
        return getattr(m, attr)

    ret = lambda mod, call: do_import('{module}.{callable}'
                                      .format(module=mod, callable=call))
    try:
        return ret(module, callable_name)
    except (ImportError, AttributeError):
        if fallback is None:
            return None
        return ret(fallback, callable_name)

SEND_ASYNC = get_config('send_async')
CELERY_TASK = import_path('submit_sms_mt_request_task',
                          get_config('celery_module'))


def async_check(func):
    ''' decorator to route API-call request to celery depending on config '''
    def _decorated(*args, **kwargs):
        if SEND_ASYNC and CELERY_TASK:
            return CELERY_TASK.apply_async(args)
        return func(*args, **kwargs)
    return _decorated

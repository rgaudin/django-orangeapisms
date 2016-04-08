#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import logging
import datetime

import iso8601

logger = logging.getLogger(__name__)
UTC = iso8601.iso8601.Utc()


def datetime_is_aware(adate):
    return adate.tzinfo is not None


def datetime_aware(adate):
    if datetime_is_aware(adate):
        return adate
    return adate.replace(tzinfo=UTC)


def datetime_from_iso(aniso):
    if aniso is None:
        return None
    return iso8601.parse_date(aniso).replace(tzinfo=None)


def datetime_to_iso(adate):
    if datetime_is_aware(adate):
        adate = adate.replace(tzinfo=None)
    isf = adate.isoformat()
    if '.' not in isf:
        isf += '.0000'
    return isf


def encode_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return "datetime:{datetime}".format(datetime=datetime_to_iso(obj))
    raise TypeError(repr(obj) + " is not JSON serializable")


def decode_datetime(obj):
    if 'datetime' not in obj:
        return obj
    _, aniso = obj.split('datetime:')
    return datetime_from_iso(aniso)


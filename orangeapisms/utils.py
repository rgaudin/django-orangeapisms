#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import datetime
import json
import logging
import urllib

import iso8601
import requests

from orangeapisms import import_path, async_check
from orangeapisms.models import SMSMessage
from orangeapisms.config import get_config

logger = logging.getLogger(__name__)
UTC = iso8601.iso8601.Utc()


def send_sms(to_addr, message,
             as_addr=get_config('default_sender_name'),
             db_save=get_config('use_db')):
    ''' SMS-MT shortcut function '''
    if not db_save:
        return submit_sms_mt(to_addr, message, as_addr)
    msg = SMSMessage.create_mt(to_addr, message,
                               as_addr, SMSMessage.PENDING)
    success = submit_sms_mt_request(msg.to_mt(), msg)
    msg.sending_status = msg.SENT if success else msg.FAILED_TO_SEND
    msg.save()
    return success, msg


@async_check
def submit_sms_mt_request(payload, message=None):
    ''' submit an SMS-MT request to Orange API '''
    return do_submit_sms_mt_request(payload, message)


def do_submit_sms_mt_request(payload, message=None):
    ''' Use submit_sms_mt_request

    actual submission of API request for SMS-MT '''
    def update_status(msg, success):
        print("updating status for {}: {}".format(msg, success))
        if msg is None:
            print("msg is none")
            return
        msg.update_status(msg.SENT if success else msg.FAILED_TO_SEND)
        print("updated status for {}".format(msg))
        return success

    url = "{api}/outbound/{addr}/requests".format(
        api=get_config('smsmt_url'),
        addr=urllib.quote_plus(payload.get('address')[-1]))
    headers = {
        'Authorization': 'Bearer {token}'
        .format(token=get_config('token')),
        'Content-type': 'application/json;charset=UTF-8'
    }
    req = requests.post(url, headers=headers, json=payload)
    resp = req.json()
    if "resourceReference" not in resp.keys():
        print("bad as no resourceReference")
        return update_status(message, False)

    if message is not None:
        message.update_reference(
            resp['resourceReference']['resourceURL'].rsplit('/', 1)[-1])
        print("is good")
        return update_status(message, True)
    return "resourceReference" in resp.keys()


def submit_sms_mt(address, message,
                  sender_name=get_config('default_sender_name'),
                  callback_data=None):
    return submit_sms_mt_request({
        "address": ["tel:{dest_addr}".format(dest_addr=address)],
        "senderName": sender_name,
        "message": message,
        "callbackData": callback_data,
    })


jsdthandler = lambda obj: obj.isoformat() \
    if isinstance(obj, datetime.datetime) \
    else json.JSONEncoder().default(obj)


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


def get_handler(slug):
    stub = 'orangeapisms.stub'
    mod = get_config('handler_module')
    if mod is None:
        mod = stub

    return import_path('handle_{}'.format(slug), module=mod, fallback=stub)

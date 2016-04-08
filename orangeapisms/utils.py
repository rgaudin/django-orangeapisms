#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import datetime
import logging
import urllib
import base64

import requests

from orangeapisms import import_path, async_check
from orangeapisms.models import SMSMessage
from orangeapisms.config import get_config, update_config

logger = logging.getLogger(__name__)
ONE_DAY = 86400


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
        if msg is None:
            return
        msg.update_status(msg.SENT if success else msg.FAILED_TO_SEND)
        return success

    sender_address = payload['outboundSMSMessageRequest']['senderAddress']
    url = "{api}/outbound/{addr}/requests".format(
        api=get_config('smsmt_url'),
        addr=urllib.quote_plus(sender_address))
    headers = {
        'Authorization': 'Bearer {token}'
        .format(token=get_token()),
        'Content-type': 'application/json;charset=UTF-8'
    }

    from pprint import pprint as pp ; pp(headers)

    from pprint import pprint as pp ; pp(payload)

    req = requests.post(url, headers=headers, json=payload)
    resp = req.json()

    from pprint import pprint as pp ; pp(resp)

    if "requestError" in resp.keys():
        exp_name = resp['requestError'].keys()[0]
        exp_data = resp['requestError'][exp_name]
        logger.error("HTTP {http_code}: {exp_name} - "
                     "{messageId}: {text} -- {variables}"
                     .format(http_code=req.status_code,
                             exp_name=exp_name,
                             messageId=exp_data['messageId'],
                             text=exp_data['text'],
                             variables=exp_data['variables']))
        return update_status(message, False)

    rurl = resp['outboundSMSMessageRequest'] \
        .get('resourceURL', '').rsplit('/', 1)[-1]
    if message is not None and rurl:
        message.update_reference(rurl)
        return update_status(message, True)
    return bool(rurl)


def submit_sms_mt(address, message,
                  sender_name=get_config('default_sender_name'),
                  callback_data=None):
    return submit_sms_mt_request(
        mt_payload(dest_addr=address,
                   message=message,
                   sender_address=get_config('sender_address'),
                   sender_name=sender_name))


def mt_payload(dest_addr, message, sender_address, sender_name):
    return {
        "outboundSMSMessageRequest": {
            "address": "tel:{dest_addr}".format(dest_addr=dest_addr),
            "outboundSMSTextMessage": {
                "message": message
            },
            "senderAddress": "tel:{src_addr}".format(src_addr=sender_address),
            "senderName": sender_name
        }
    }


def get_handler(slug):
    stub = 'orangeapisms.stub'
    mod = get_config('handler_module')
    if mod is None:
        mod = stub

    return import_path('handle_{}'.format(slug), module=mod, fallback=stub)


def get_token():
    token_expiry = get_config('token_expiry')
    if token_expiry is None or token_expiry < datetime.datetime.now() \
            + datetime.timedelta(days=0, seconds=60):
        assert request_token()
    return get_config('token')


def request_token():
    url = "{oauth_url}/token".format(oauth_url=get_config('oauth_url'))
    basic_header = base64.b64encode(
        "{client_id}:{client_secret}".format(
            client_id=get_config('client_id'),
            client_secret=get_config('client_secret')))
    headers = {'Authorization': "Basic {b64}".format(b64=basic_header)}
    payload = {'grant_type': 'client_credentials'}
    req = requests.post(url, headers=headers, data=payload)
    resp = req.json()
    if "token_type" in resp:
        expire_in = int(resp['expires_in'])
        token_data = {
            'token': resp['access_token'],
            'token_expiry': datetime.datetime.now() + datetime.timedelta(
                days=expire_in / ONE_DAY,
                seconds=expire_in % ONE_DAY) - datetime.timedelta(
                days=0, seconds=60)}
        update_config(token_data, save=True)
        return token_data
    else:
        logger.error("HTTP {http} {error}: {description}".format(
            http=req.status_code,
            error=resp['error'],
            description=resp['error_description']))
        return False

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import datetime
import logging
import urllib
import base64
import re

import requests
import pytz

from orangeapisms import import_path, async_check
from orangeapisms.models import SMSMessage
from orangeapisms.config import get_config, update_config
from orangeapisms.datetime import datetime_from_iso
from orangeapisms.exceptions import OrangeAPIError

logger = logging.getLogger(__name__)
ONE_DAY = 86400
SMS_SERVICE = 'SMS_OCB'
API_TZ = pytz.timezone('Europe/Paris')
UTC = pytz.utc


def cleaned_msisdn(to_addr):
    """ fixes common mistakes to make to_addr a MSISDN

        - removes extra chars
        - starts with a +
        - adds prefix if it seems missing """

    if not get_config('fix_msisdn'):
        return to_addr

    to_addr = re.sub(r"^00", "+", to_addr)

    # if a suffix was supplied, fix chars only
    if to_addr.startswith('+'):
        return "+{addr}".format(addr=re.sub(r"\D", "", to_addr))

    # no prefix, make sure to remove default prefix if present and fix chars
    prefix = get_config('country_prefix')
    to_addr = re.sub(r"\D", "", to_addr)
    if to_addr.startswith(prefix):
        to_addr = re.sub(r"^{prefix}".format(prefix=prefix), "", to_addr)
    return "+{prefix}{addr}".format(prefix=prefix, addr=to_addr)


def send_sms(to_addr, message,
             as_addr=get_config('default_sender_name'),
             db_save=get_config('use_db')):
    ''' SMS-MT shortcut function '''
    to_addr = cleaned_msisdn(to_addr)
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


def do_submit_sms_mt_request(payload, message=None, silent_failure=False):
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
    headers = get_standard_header()

    req = requests.post(url, headers=headers, json=payload)

    try:
        assert req.status_code == 201
        resp = req.json()
    except AssertionError:
        exp = OrangeAPIError.from_request(req)
        logger.error("Unable to transmit SMS-MT. {exp}".format(exp=exp))
        logger.exception(exp)
        update_status(message, False)
        if not silent_failure:
            raise exp
        return False

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
        mt_payload(dest_addr=cleaned_msisdn(address),
                   message=message,
                   sender_address=get_config('sender_address'),
                   sender_name=sender_name))


def mt_payload(dest_addr, message, sender_address, sender_name):
    return {
        "outboundSMSMessageRequest": {
            "address": "tel:{dest_addr}".format(
                dest_addr=cleaned_msisdn(dest_addr)),
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


def get_standard_header():
    return {
        'Authorization': 'Bearer {token}'.format(token=get_token()),
        'Content-type': 'application/json;charset=UTF-8'
    }


def request_token(silent_failure=False):
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
        exp = OrangeAPIError.from_request(req)
        logger.error("Unable to retrieve token. {}".format(exp))
        logger.exception(exp)
        if not silent_failure:
            raise exp
        return False


def get_contracts(silent_failure=False):
    url = "{api}/contracts".format(api=get_config('smsadmin_url'))
    headers = get_standard_header()

    req = requests.get(url, headers=headers)
    try:
        assert req.status_code == 200
        return req.json()
    except AssertionError:
        exp = OrangeAPIError.from_request(req)
        logger.error("Unable to retrieve contracts. {exp}".format(exp=exp))
        logger.exception(exp)
        if not silent_failure:
            raise exp


def get_sms_balance(country=get_config('country')):
    contracts = get_contracts()
    expiry = None
    balance = 0
    for contract in contracts.get('partnerContracts', {}).get('contracts', []):
        if not contract['service'] == SMS_SERVICE:
            continue

        for sc in contract.get('serviceContracts', []):
            if not sc['country'] == country:
                continue

            if not sc['service'] == SMS_SERVICE:
                continue

            balance += sc['availableUnits']
            expires = datetime_from_iso(sc['expires'])
            if expiry is None or expiry < expires:
                expiry = expires
    if expiry is not None:
        expiry = API_TZ.localize(expiry)
    return balance, expiry

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import logging
import re
import uuid
from collections import OrderedDict

from django.db import models
from django.utils import timezone

from orangeapisms.config import get_config
from orangeapisms.datetime import datetime_from_iso

logger = logging.getLogger(__name__)


class SMSMessage(models.Model):

    class Meta:
        ordering = ['-created_on']

    INCOMING = 'incoming'
    OUTGOING = 'outgoing'

    DIRECTIONS = {
        INCOMING: "Incoming",
        OUTGOING: "Outgoing",
    }

    MO = 'sms-mo'
    MT = 'sms-mt'
    DR = 'sms-mt+dr'

    TYPES = {
        MO: "SMS-MO",
        MT: "SMS-MT",
        DR: "SMS-MT+DR"
    }

    PENDING = 'pending'
    SENT = 'sent'
    FAILED_TO_SEND = 'failed_to_send'
    RECEIVED = 'received'
    DELIVERED = 'delivered'
    NOT_DELIVERED = 'not_delivered'

    STATUSES = OrderedDict([
        (PENDING, "Not Sent Yet"),  # SMS-MT to be sent
        (SENT, "Sent"),  # SMS-MT sent
        (FAILED_TO_SEND, "Failed to send"),  # SMS-MT sending failed
        (RECEIVED, "Received"),  # SMS-MO received
        (DELIVERED, "Delivered"),  # SMS-MT delivered to terminal
        (NOT_DELIVERED, "Not Delivered"),  # SMS-MT failed to deliver
    ])

    DELIVERY_STATUS_MATRIX = OrderedDict([
        ("DeliveredToTerminal", DELIVERED),
        ("DeliveredToNetwork", DELIVERED),  # not exactly but...
        ("DeliveryUncertain", NOT_DELIVERED),
        ("DeliveryImpossible", NOT_DELIVERED),
        ("MessageWaiting", NOT_DELIVERED),
    ])

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4,
                            editable=False)

    direction = models.CharField(max_length=64, choices=DIRECTIONS.items())
    sms_type = models.CharField(max_length=64, choices=TYPES.items())

    created_on = models.DateTimeField(auto_now_add=True)
    delivery_status_on = models.DateTimeField(null=True, blank=True)

    sender_address = models.CharField(max_length=255, blank=True, null=True)
    destination_address = models.CharField(
        max_length=255, blank=True, null=True)

    # incoming only
    message_id = models.CharField(max_length=64, blank=True, null=True)

    # outgoing only
    reference_code = models.CharField(max_length=64, blank=True, null=True)

    content = models.CharField(max_length=1600)
    status = models.CharField(max_length=64, choices=STATUSES.items())

    def __str__(self):
        return self.__unicode__().encode('UTF-8')

    def __unicode__(self):
        return "{type}: {uuid}".format(type=self.sms_type_verbose,
                                       uuid=self.suuid)

    @property
    def sms_type_verbose(self):
        return self.TYPES.get(self.sms_type)

    @property
    def status_verbose(self):
        return self.STATUSES.get(self.status)

    @classmethod
    def get_or_none(cls, uuid):
        try:
            return cls.objects.get(uuid=uuid)
        except cls.DoesNotExist:
            return None

    @property
    def identity(self):
        if self.direction == self.INCOMING:
            return self.sender_address
        else:
            return self.destination_address

    @classmethod
    def create_from_payload(cls, payload):
        action = payload.keys().pop()
        if action == 'deliveryInfoNotification':
            return cls.record_dr_from_payload(payload.get(action))
        elif action == 'inboundSMSMessageNotification':
            return cls.create_mo_from_payload(payload.get(action))
        else:
            raise ValueError("Payload doesn't contain SMS-MO not SMS-DR")

    @classmethod
    def clean_address(cls, address):
        return re.sub(r'^tel\:', '', address)

    @classmethod
    def create_mo_from_payload(cls, payload):
        kwargs = {
            'direction': cls.INCOMING,
            'sms_type': cls.MO,
            'status': cls.RECEIVED,

            'sender_address': cls.clean_address(payload.get('senderAddress')),
            'destination_address':
                cls.clean_address(payload.get('destinationAddress')),
            'message_id': payload.get('messageId'),
            'content': payload.get('message'),
            'created_on': datetime_from_iso(payload.get('dateTime'))
        }
        if not get_config('use_db'):
            return cls(**kwargs)
        return cls.objects.create(**kwargs)

    @classmethod
    def record_dr_from_payload(cls, payload):
        # no DR support in non-DB mode
        if not get_config('use_db'):
            return

        uuid = payload.get('callbackData')
        msg = cls.get_or_none(uuid)
        if msg is None:
            raise ValueError("SMS-DR reference unreachable SMS-MT `{uuid}`"
                             .format(uuid=uuid))
        kwargs = {
            'sms_type': cls.DR,
            'delivery_status_on': payload.get('delivery_status_on',
                                              timezone.now()),
            'status': cls.DELIVERY_STATUS_MATRIX.get(
                payload.get('deliveryInfo', {})
                       .get('deliveryStatus', cls.NOT_DELIVERED))
        }
        msg.update(**kwargs)
        msg.save()
        return msg

    @classmethod
    def create_mt(cls, destination_address, content,
                  sender_address=None, sending_status=SENT):
        kwargs = {
            'direction': cls.OUTGOING,
            'sms_type': cls.MT,
            'created_on': timezone.now(),

            'sender_address': sender_address,
            'destination_address': destination_address,
            'content': content,
            'status': sending_status,
        }
        if not get_config('use_db'):
            return cls(**kwargs)
        return cls.objects.create(**kwargs)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_mt(self):
        from orangeapisms.utils import mt_payload
        return mt_payload(dest_addr=self.destination_address,
                          message=self.content,
                          sender_address=get_config('sender_address'),
                          sender_name=self.sender_address)

    @property
    def suuid(self):
        return self.uuid.get_hex() or None

    def update_reference(self, reference_code):
        self.reference_code = reference_code
        if not get_config('use_db'):
            return
        self.save()

    def update_status(self, status):
        self.status = status
        if not get_config('use_db'):
            return
        self.save()

    def reply(self, text, as_addr):
        from orangeapisms.utils import send_sms
        return send_sms(to_addr=self.sender_address,
                        message=text,
                        as_addr=as_addr)

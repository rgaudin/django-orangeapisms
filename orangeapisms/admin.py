#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

from django.contrib import admin

from orangeapisms.models import SMSMessage


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_on'
    list_display = ('sms_type', 'created_on', 'identity', 'content', 'status')
    list_display_links = ('created_on', )
    list_filter = ('sms_type', 'direction', 'status',)
    search_fields = ['sender_address', 'destination_address', 'content']

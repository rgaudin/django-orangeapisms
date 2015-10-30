#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

''' Stub handler module for OrangeAPISMS

    Copy handlers definitions to your module and change the
    ORANGE_API_HANDLER_MODULE value in your settings. '''


def handle_smsmo(message):
    ''' Handles an incoming SMSMessage '''
    return


def handle_smsdr(message):
    ''' Handles an Incoming Delivery Receipt for a sent SMS-MT

        message parameter is the SMS-MT, updated with DR info '''
    return


def handle_smsmt(message):
    ''' Called right after an SMS-MT is sent successfuly '''
    return

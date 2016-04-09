#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

from django.conf.urls import url
from orangeapisms import views

urlpatterns = [
    # Public index
    url(r'^$', views.home, name='oapisms_home'),

    # SMS-MO API endpoint
    url(r'^smsmo/?$', views.smsmo,
        name='oapisms_mo'),

    # SMS-DR API endpoint
    url(r'^smsdr/?$', views.smsdr,
        name='oapisms_dr'),

    # in-browser tester
    url(r'^tester/smsmt/?$', views.form_view,
        {'form_name': 'smsmt', 'action_name': "Send SMS-MT"},
        name='oapisms_tester_smsmt'),
    url(r'^tester/fsmsmt/?$', views.form_view,
        {'form_name': 'fsmsmt', 'action_name': "Create Fake SMS-MT"},
        name='oapisms_tester_fsmsmt'),
    url(r'^tester/fsmsmo/?$', views.form_view,
        {'form_name': 'fsmsmo', 'action_name': "Create Fake SMS-MO"},
        name='oapisms_tester_fsmsmo'),
    url(r'^tester/fsmsdr/?$', views.form_view,
        {'form_name': 'fsmsdr', 'action_name': "Create Fake SMS-DR"},
        name='oapisms_tester_fsmsdr'),
    url(r'^tester/logs/?$', views.logs,
        name='oapisms_tester_logs'),
    url(r'^tester/balance/?$', views.check_balance,
        name='oapisms_tester_balance'),
    url(r'^tester/?$', views.tester,
        name='oapisms_tester'),
]

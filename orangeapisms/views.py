#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import json
import logging

from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django import forms
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from orangeapisms.models import SMSMessage
from orangeapisms.utils import (get_handler, send_sms,
                                get_sms_balance, clean_msisdn)
from orangeapisms.datetime import datetime_to_iso
from orangeapisms.config import get_config

logger = logging.getLogger(__name__)
handle_smsmo = get_handler('smsmo')
handle_smsmt = get_handler('smsmt')
handle_smsdr = get_handler('smsdr')


def activated(aview):
    ''' disable view based on config '''

    def _decorated(*args, **kwargs):
        if not get_config('enable_tester', False):
            raise PermissionDenied
        return aview(*args, **kwargs)
    return _decorated


class SMSMTForm(forms.Form):
    destination_address = forms.CharField(
        widget=forms.TextInput(attrs={'required': True,
                                      'max_length': 255}))
    sender_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': get_config('default_sender_name'),
            'max_length': 255}))
    content = forms.CharField(widget=forms.Textarea(
        attrs={'rows': 3, 'max_length': 1600, 'required': True}))

    @classmethod
    def get_initial(cls):
        return {}

    def clean_destination_address(self):
        return clean_msisdn(self.cleaned_data.get('destination_address'))


class FSMSMTForm(SMSMTForm):
    status = forms.ChoiceField(choices=SMSMessage.STATUSES.items())


class FSMSMOForm(forms.Form):
    sender_address = forms.CharField(
        widget=forms.TextInput(attrs={'required': True,
                                      'max_length': 255}))
    created_on = forms.DateTimeField()
    destination_address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': get_config('sender_address'),
            'max_length': 255}))
    message_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'max_length': 64,
                                      'required': False}))
    content = forms.CharField(widget=forms.Textarea(
        attrs={'rows': 3, 'max_length': 1600, 'required': True}))

    @classmethod
    def get_initial(cls):
        return {'created_on': timezone.now()}

    def clean_destination_address(self):
        return clean_msisdn(self.cleaned_data.get('destination_address'))


class FSMSDRForm(forms.Form):
    uuid = forms.UUIDField(
        widget=forms.TextInput(attrs={'required': True}))
    delivery_on = forms.DateTimeField()
    status = forms.ChoiceField(
        choices=[(k, k) for k in SMSMessage.DELIVERY_STATUS_MATRIX.keys()])

    @classmethod
    def get_initial(cls):
        return {'delivery_on': timezone.now()}

FORM_MAP = {
    'smsmt': SMSMTForm,
    'fsmsmt': FSMSMTForm,
    'fsmsmo': FSMSMOForm,
    'fsmsdr': FSMSDRForm,
}


def home(request):
    context = {'page': 'home',
               'disable_tester': not get_config('enable_tester', False)}

    from django.core.urlresolvers import reverse

    url_mo = request.build_absolute_uri(reverse('oapisms_mo'))
    url_mt = request.build_absolute_uri(reverse('oapisms_dr'))
    context.update({
        'endpoints': [
            ('SMS-MO', url_mo),
            ('SMS-DR', url_mt),
        ]
    })

    return render(request, 'orangeapisms/home.html', context)


@activated
def tester(request):
    return redirect('oapisms_tester_smsmt')


@activated
def check_balance(request):
    now = timezone.now()
    balance, expiry = get_sms_balance()

    if expiry <= now:
        balance_msg = "{balance} remaining SMS expired on {date}. Top-up " \
                      "account to extend expiry date ({country})"
    else:
        balance_msg = "{balance} SMS remaining until {date} ({country})"
    try:
        feedback = balance_msg.format(balance=balance,
            country=get_config('country'), date=expiry.strftime('%c'))
        lvl = messages.INFO
    except Exception as e:
        feedback = e.__str__()
        lvl = messages.WARNING
    messages.add_message(request, lvl, feedback)
    return redirect('oapisms_tester')


@activated
def form_view(request, form_name, action_name="Submit"):
    context = {}

    # setup basic forms
    form_cls = FORM_MAP.get(form_name)
    form = form_cls(initial=form_cls.get_initial())

    # actual handling of events
    def handle_request(active_form, form):
        if active_form == 'smsmt':
            success, msg = send_sms(
                to_addr=form.cleaned_data.get('destination_address'),
                message=form.cleaned_data.get('content'),
                as_addr=form.cleaned_data.get('sender_name')
                or get_config('default_sender_name'))
            handle_smsmt(msg)
            return success, "Sent {}".format(msg)

        elif active_form == 'fsmsmt':
            msg = SMSMessage.create_mt(
                destination_address=form.cleaned_data.get(
                    'destination_address'),
                content=form.cleaned_data.get('content'),
                sender_address=form.cleaned_data.get('sender_address'),
                sending_status=form.cleaned_data.get('status'))
            handle_smsmo(msg)
            return True, "Sent {}".format(msg)

        elif active_form == 'fsmsmo':
            msg = SMSMessage.create_mo_from_payload({
                'senderAddress': "tel:{}".format(
                    form.cleaned_data.get('sender_address')),
                'destinationAddress': form.cleaned_data.get(
                    'destination_address'),
                'messageId': form.cleaned_data.get('message_id') or None,
                'message': form.cleaned_data.get('content'),
                'dateTime': datetime_to_iso(
                    form.cleaned_data.get('created_on'))
            })
            handle_smsmo(msg)
            return True, "Received {}".format(msg)

        elif active_form == 'fsmsdr':
            msg = SMSMessage.record_dr_from_payload({
                'callbackData': form.cleaned_data.get('uuid'),
                'delivery_status_on': datetime_to_iso(
                    form.cleaned_data.get('delivery_on')),
                'deliveryInfo': {
                    'deliveryStatus': form.cleaned_data.get('status')
                }
            })
            return True, "Updated {}".format(msg)

        else:
            return False, "Unknown action `{}`".format(active_form)

    if request.method == "POST":
        form = form_cls(request.POST)
        if form.is_valid():
            logger.info("Form {} is valid".format(request.POST.get('action')))

            try:
                success, feedback = handle_request(form_name, form)
            except Exception as e:
                logger.exception(e)
                success = False
                feedback = e.__str__()

            lvl = messages.SUCCESS if success else messages.WARNING
            messages.add_message(request, lvl, feedback)
            context.update({'success': success, 'feedback': feedback})
        else:
            pass  # display form errors
    else:
        pass

    context.update({
        'form': form,
        'view_name': 'oapisms_tester_{}'.format(form_name),
        'page': form_name,
        'action_name': action_name,
    })

    return render(request, 'orangeapisms/tester_form.html', context)


@activated
def logs(request):

    context = {'page': 'logs'}

    messages_list = SMSMessage.objects.all().order_by('-created_on')
    paginator = Paginator(messages_list, 25)
    page = request.GET.get('page')

    try:
        messages_log = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        messages_log = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        messages_log = paginator.page(paginator.num_pages)

    context.update({'messages_log': messages_log,
                    'paginator': paginator})

    return render(request, 'orangeapisms/tester_logs.html', context)


@csrf_exempt
@require_POST
def smsmo(request, **options):

    payload = json.loads(request.body)[
        'inboundSMSMessageNotification']['inboundSMSMessage']

    msg = SMSMessage.create_mo_from_payload(payload)

    try:
        handle_smsmo(msg)
    except Exception as e:
        logger.error("Exception in SMS-MO processing #{}".format(msg.suuid))
        logger.exception(e)
        status = 301
    else:
        status = 200

    return JsonResponse({"UUID": msg.suuid}, status=status)


@csrf_exempt
@require_POST
def smsdr(request, **options):

    payload = json.loads(request.body)['deliveryInfoNotification']

    msg = SMSMessage.record_dr_from_payload(payload)

    try:
        handle_smsdr(msg)
    except Exception as e:
        logger.error("Exception in SMS-DR processing #{}".format(msg.suuid))
        logger.exception(e)
        status = 301
    else:
        status = 200

    return JsonResponse({"UUID": msg.suuid}, status=status)

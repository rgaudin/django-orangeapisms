# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-24 11:34
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SMSMessage',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('direction', models.CharField(choices=[('incoming', 'Incoming'), ('outgoing', 'Outgoing')], max_length=64)),
                ('sms_type', models.CharField(choices=[('sms-mo', 'SMS-MO'), ('sms-mt', 'SMS-MT'), ('sms-mt+dr', 'SMS-MT+DR')], max_length=64)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('delivery_status_on', models.DateTimeField(blank=True, null=True)),
                ('sender_address', models.CharField(blank=True, max_length=255, null=True)),
                ('destination_address', models.CharField(blank=True, max_length=255, null=True)),
                ('message_id', models.CharField(blank=True, max_length=64, null=True)),
                ('reference_code', models.CharField(blank=True, max_length=64, null=True)),
                ('content', models.CharField(max_length=1600)),
                ('status', models.CharField(choices=[('pending', 'Not Sent Yet'), ('sent', 'Sent'), ('failed_to_send', 'Failed to send'), ('received', 'Received'), ('delivered', 'Delivered'), ('not_delivered', 'Not Delivered')], max_length=64)),
            ],
            options={
                'ordering': ['-created_on'],
            },
        ),
    ]

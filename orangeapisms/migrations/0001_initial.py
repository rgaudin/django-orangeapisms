# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SMSMessage',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('direction', models.CharField(max_length=64, choices=[('outgoing', 'Outgoing'), ('incoming', 'Incoming')])),
                ('sms_type', models.CharField(max_length=64, choices=[('sms-mt', 'SMS-MT'), ('sms-mo', 'SMS-MO'), ('sms-mt+dr', 'SMS-MT+DR')])),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('delivery_status_on', models.DateTimeField(null=True, blank=True)),
                ('sender_address', models.CharField(max_length=255, null=True, blank=True)),
                ('destination_address', models.CharField(max_length=255, null=True, blank=True)),
                ('message_id', models.CharField(max_length=64, null=True, blank=True)),
                ('reference_code', models.CharField(max_length=64, null=True, blank=True)),
                ('content', models.CharField(max_length=1600)),
                ('status', models.CharField(max_length=64, choices=[('pending', 'Not Sent Yet'), ('sent', 'Failed to send'), ('received', 'Received'), ('delivered', 'Delivered'), ('not_delivered', 'Not Delivered')])),
            ],
            options={
                'ordering': ['-created_on'],
            },
        ),
    ]

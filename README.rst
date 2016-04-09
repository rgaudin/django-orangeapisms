orangeapisms
=========================

Django app to add support for Orange API SMS-MO and SMS-MT (with DR)

Install
--------

* `pip install orangeapisms`
* Edit your `settings.py` file and add: 

.. code-block:: python

    INSTALLED_APPS = list(INSTALLED_APPS) + ['orangeapisms', 'django_forms_bootstrap']

* Configure your `orangeapi.json` file (place it next to your `settings.py` file): 

.. code-block:: json

    {
        "handler_module": "myapp.orange_handler",
        "use_db": true,
        "sender_address": "+22300000000",
        "sender_name": "POTUS",
        "client_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "client_secret": "xxxxxxxxxxxxxxxx",
        "enable_tester": true,
        "default_sender_name": "sender_address"
    }

* Setup Database with `./manage.py migrate`

That's it ! Test it by accessing `/oapi/` and playing with the tester.

:**client_id**:          Your Client ID (mandatory)
:**client_secret**:      Your Client Secret (mandatory)
:**handler_module**:     python path to your module handling messages (mandatory)
:use_db:                 whether to store SMS in DB (SMSMessage Model)
:smsmt_url:              URL of your API (might change depending on your plan)
:oauth_url:              OAuth URL for Orange API
:sender_address:         Your subscribed phone number
:sender_name:            Your custom sender name (can be number or string)
:enable_tester:          To enable tester & logs WebUI on /oapi/
:default_sender_name:    What to use as default sender name
:send_async:             whether to deffer SMS sending to celery
:celery_module:          python path to your celery tasks module
:country:                ISO 3166-1 code for your country (used for balance checking)
:fix_msisdn:             whether to fix SMS-MT destination without prefix
:country_prefix:         MSISDN numeric prefix for your country (to fix SMS-MT without prefix)


Usage
--------

After installation (previous step), you are able to send & receive individual SMS.
To automatically process incoming SMS, you will have to customise the *handler module* which you specified in `ORANGE_API['handler_module']`.

The module would call three different functions based on events:

* `smsmo(message)` on an incoming SMS-MO
* `smsmt(message)` on an outgoing (sent by you) SMS-MT
* `smsdr(message)` on an incoming delivery-receipt notification. The passed message is the SMS-MT which received the DR. 



**Sample handler module:**

.. code-block:: python

    import datetime
    import logging    

    from orangeapisms.utils import send_sms
    from myapp.models import UserModel    

    logger = logging.getLogger(__name__)    
    

    def handle_smsmo(message):
        logger.info("Received an SMS-MO: {}".format(message))    

        def register_user(message, keyword, text):
            # break-down the formatted SMS into variables
            try:
                name, sex, dob = text.split()
            except:
                return message.reply('Invalid format')    

            # valid user entries
            if sex not in ['m', 'f']:
                return message.reply('Unable to understand sex')    

            # reuse input into different data structure
            try:
                d = dob.split('-')
                birthdate = datetime.datetime(d[3], d[2], d[1])
            except:
                return message.reply('Unable to understand date of birth')    

            # make use of the data including message metadata
            user = UserModel.objects.create(
                name=name, sex=sex, dob=birthdate,
                phone=message.sender_address)    

            return message.reply("Congratulations, you're registered as #{}"
                                 .format(user.id))    

        def broadcast_to_users(message, keyword, text):
            # loop on all Users in DB
            for user in UserModel.objects.all():
                # send a custom message to that user
                send_sms(user.phone, "Hey {u}, {c}".format(u=user.name, c=text))    

        keywords = {
            'register': register_user,
            'broadcast': broadcast_to_users,
        }    

        # find the proper keyword
        keyword, text = message.content.split(' ', 1)
        if keyword in keywords.keys():
            return keywords.get(keyword)(message, keyword, text.strip().lower())    

        # fallback on error
        return message.reply('Unknown request')    
    

    def handle_smsmt(message):
        logger.info("Sent an SMS-MT: {}".format(message))    
    

    def handle_smsdr(message):
        logger.info("Received an SMS-DR: {}".format(message))

Using a broker to send SMS-MT
-----------------------------

By default, SMS-MT are sent synchronously meaning your request is stalled until the API call is complete.

If you need to send multiple SMS-MT while not blocking the request thread, you will want to defer sending to a broker.

This library integrates easily with `celery` so you can do just that in a breeze.

To use Asynchronous SMS-MT sending, you will need to :

* Install and configure celery onto your project (see instructions bellow if needed)
* Edit your `settings.py` to include the following options

.. code-block:: python

    # wether to send asynchronously or not
    'send_async': True,
    # python path of your celery module containing the task
    'celery_module': 'myproject.celery'

* Add a custom task to your celery module

.. code-block:: python

	@app.task()
	def submit_sms_mt_request_task(payload, message):
	    from orangeapisms.utils import do_submit_sms_mt_request
	    return do_submit_sms_mt_request(payload, message)

That's it. Now every SMS-MT will be deferred to celery and processed by your broker.

Launch a `celery` worker to test it!

Basic celery configuration
--------------------------

If you are not familiar with celery and want to quickly test the async feature, follow this steps:

* Install redis on your computer and start it

.. code-block:: bash

    sudo apt-get install redis
    service redis start

* Install celery and redis with ```pip install celery redis```

* Add the celery configuration to your `settings.py`:

.. code-block:: python

    BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

* Create a module in your project for `celery`:

.. code-block:: python

    import os    

    from celery import Celery    

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    app = Celery('project')
    app.config_from_object('django.conf:settings')    
    

    @app.task()
    def submit_sms_mt_request_task(payload, message):
        from orangeapisms.utils import do_submit_sms_mt_request
        return do_submit_sms_mt_request(payload, message)

* Launch a worker

.. code-block:: python

    celery -A project worker -l info

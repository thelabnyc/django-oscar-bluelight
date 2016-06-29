===============================
Django Oscar Bluelight Specials
===============================

|  |license| |kit| |format| |downloads|

This package contains enhancements and improvements to the built-in offers and vouchers features in Django Oscar.


Features
========

- **Group Restricted Vouchers**: Bluelight adds the ability to restrict application of vouchers to a specific whitelist of groups (`django.contrib.auth.models.Group`). For example, you could create a voucher code that can only be applied by users who belong to the group *Customer Service Reps*.
- **Compound Offer Conditions**: By default, Oscar only allows assigning a single condition to a promotional offer. Compound offer conditions allow you to create more complex logic around when an offer should be enabled. For example, you could create a compound condition specifying that a basket must contain at least 3 items *and* have a total value greater than $50.
    - Compound conditions can aggregate an unlimited number of child conditions together.
    - Compound conditions can join their child conditions using either an *AND* or an *OR* conjunction.
    - Very complex conditions requiring both *AND* and *OR* conjunctions can be modeled by creating multiple levels of compound conditions.
- **Parent / Child Voucher Codes**: By default Oscar doesn't support bulk creation of voucher codes. Bluelight adds the ability to bulk create any number of child vouchers (with unique, automatically generated codes) for any standard (non-child) voucher. This can be useful when sending voucher codes to customer's through email, as it allows the creation of hundreds or thousands of non-sequential, one-time-use codes.
    - Child codes can be added when creating a new voucher or after a voucher is created.
    - More child codes can be generated for a voucher at any time.
    - Child codes can be exported in CSV and JSON formats.
    - Any time a parent voucher is edited (name changed, benefit altered, etc), all child codes are also updated to match.
    - When a parent voucher is deleted, all children are also deleted.
    - Once a voucher has child codes assigned to it, the parent voucher itself can not be applied by anyone.


Roadmap
=======

- Make child code creation and updating more performant, possibly by (1) extracting some of the work into asynchronous Celery tasks and (2) better tracking of dirty model fields before saving.
- Add ability to duplicate vouchers.
- Add ability to add conditions to vouchers.

Caveats
=======

Bluelight currently works by forking four of Oscar's apps: offer, voucher, dashboard.offers, and dashboard.vouchers. Currently there is no way to use Bluelight if your application has already forked those applications.


Installation
============

Install `django-oscar-bluelight`.::

    $ pip install django-oscar-bluelight

Import Bluelight's settings into your projects `settings.py` file.::

    from oscar.defaults import *
    from oscarbluelight.defaults import OSCAR_DASHBOARD_NAVIGATION # Needed so that Bluelight's views show up in the dashboard
    from oscar import OSCAR_MAIN_TEMPLATE_DIR, get_core_apps
    from oscarbluelight import BLUELIGHT_TEMPLATE_DIR

Add Bluelight to your install apps.::

    INSTALLED_APPS = [
        ...
    ] + get_core_apps([
        ...
        'oscarbluelight.dashboard.offers',
        'oscarbluelight.dashboard.vouchers',
        'oscarbluelight.offer',
        'oscarbluelight.voucher',
        ...
    ])

Add Bluelight's template directory directly before Oscar's.::

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [
                BLUELIGHT_TEMPLATE_DIR,
                OSCAR_MAIN_TEMPLATE_DIR,
            ],
            ...
        }
    ]


Usage
=====

After installation, the new functionality will show up in the Oscar dashboard under the Offers menu.


Changelog
=========

0.2.2
------------------
- Fix bug preventing Voucher.groups form field from being blank

0.2.1
------------------
- Fix bug the excluded templates from package.

0.2.0
------------------
- Renamed package to `oscarbluelight` to have consistent naming with other Oscar projects.

0.1.1
------------------
- Fix bug the excluded templates from package.

0.1.0
------------------
- Initial release.


.. |license| image:: https://img.shields.io/pypi/l/django-oscar-bluelight.svg
    :target: https://pypi.python.org/pypi/django-oscar-bluelight
.. |kit| image:: https://badge.fury.io/py/django-oscar-bluelight.svg
    :target: https://pypi.python.org/pypi/django-oscar-bluelight
.. |format| image:: https://img.shields.io/pypi/format/django-oscar-bluelight.svg
    :target: https://pypi.python.org/pypi/django-oscar-bluelight
.. |downloads| image:: https://img.shields.io/pypi/dm/django-oscar-bluelight.svg?maxAge=2592000
    :target: https://pypi.python.org/pypi/django-oscar-bluelight

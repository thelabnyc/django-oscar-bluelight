# Django Oscar Bluelight Specials

[![license](https://img.shields.io/pypi/l/django-oscar-bluelight.svg)](https://pypi.python.org/pypi/django-oscar-bluelight)
[![kit](https://badge.fury.io/py/django-oscar-bluelight.svg)](https://pypi.python.org/pypi/django-oscar-bluelight)
[![format](https://img.shields.io/pypi/format/django-oscar-bluelight.svg)](https://pypi.python.org/pypi/django-oscar-bluelight)

This package contains enhancements and improvements to the built-in
offers and vouchers features in Django Oscar.

## Features

-   **Group Restricted Vouchers**: Bluelight adds the ability to restrict application of vouchers to a specific whitelist of groups (`django.contrib.auth.models.Group`). For example, you could create a voucher code that can only be applied by users who belong to the group _Customer Service Reps_.
-   **Compound Offer Conditions**: By default, Oscar only allows assigning a single condition to a promotional offer. Compound offer conditions allow you to create more complex logic around when an offer should be enabled. For example, you could create a compound condition specifying that a basket must contain at least 3 items _and_ have a total value greater than $50.
    -   Compound conditions can aggregate an unlimited number of child conditions together.
    -   Compound conditions can join their child conditions using either an _AND_ or an _OR_ conjunction.
    -   Very complex conditions requiring both _AND_ and _OR_ conjunctions can be modeled by creating multiple levels of compound conditions.
-   **Parent / Child Voucher Codes**: By default Oscar doesn't support bulk creation of voucher codes. Bluelight adds the ability to bulk create any number of child vouchers (with unique, automatically generated codes) for any standard (non-child) voucher. This can be useful when sending voucher codes to customer's through email, as it allows the creation of hundreds or thousands of non-sequential, one-time-use codes.
    -   Child codes can be added when creating a new voucher or after a voucher is created.
    -   More child codes can be generated for a voucher at any time.
    -   Child codes can be exported in CSV and JSON formats.
    -   Any time a parent voucher is edited (name changed, benefit altered, etc), all child codes are also updated to match.
    -   When a parent voucher is deleted, all children are also deleted.
    -   Once a voucher has child codes assigned to it, the parent voucher itself can not be applied by anyone.

## Roadmap

-   Make child code creation and updating more performant, possibly by (1) extracting some of the work into asynchronous Celery tasks and (2) better tracking of dirty model fields before saving.
-   Add ability to duplicate vouchers.
-   Add ability to add conditions to vouchers.

## Caveats

Bluelight currently works by forking four of Oscar's apps: offer,
voucher, dashboard.offers, and dashboard.vouchers. Currently there is no
way to use Bluelight if your application has already forked those
applications.

## Installation

Install [django-oscar-bluelight]{.title-ref}.:

```sh
pip install django-oscar-bluelight
```

Import Bluelight's settings into your projects `settings.py` file.

```py
from oscar.defaults import *
from oscarbluelight.defaults import *  # Needed so that Bluelight's views show up in the dashboard
```

Add Bluelight to your installed apps (replacing the equivalent Django
Oscar apps). The top-level `oscarbluelight` app must be defined before
the `oscar` app---if it isn't Django will not correctly find the
Bluelight's templates.

```py
INSTALLED_APPS = [
    ...
    # Bluelight. Must come before `django-oscar` so that template inheritance / overrides work correctly.
    'oscarbluelight',
    'thelabdb.pgviews',

    # django-oscar
    'oscar',
    'oscar.apps.analytics',
    'oscar.apps.checkout',
    'oscar.apps.address',
    'oscar.apps.shipping',
    'oscar.apps.catalogue',
    'oscar.apps.catalogue.reviews',
    'sandbox.partner',  # 'oscar.apps.partner',
    'sandbox.basket',  # 'oscar.apps.basket',
    'oscar.apps.payment',
    'oscarbluelight.offer',  # 'oscar.apps.offer',
    'oscar.apps.order',
    'oscar.apps.customer',
    'oscar.apps.search',
    'oscarbluelight.voucher',  # 'oscar.apps.voucher',
    'oscar.apps.wishlists',
    'oscar.apps.dashboard',
    'oscar.apps.dashboard.reports',
    'oscar.apps.dashboard.users',
    'oscar.apps.dashboard.orders',
    'oscar.apps.dashboard.catalogue',
    'oscarbluelight.dashboard.offers',  # 'oscar.apps.dashboard.offers',
    'oscar.apps.dashboard.partners',
    'oscar.apps.dashboard.pages',
    'oscar.apps.dashboard.ranges',
    'oscar.apps.dashboard.reviews',
    'oscarbluelight.dashboard.vouchers',  # 'oscar.apps.dashboard.vouchers',
    'oscar.apps.dashboard.communications',
    'oscar.apps.dashboard.shipping',
    ...
]
```

Fork the basket application in your project and add
`BluelightBasketMixin` as a parent class of the `Line` model.

```py
from oscar.apps.basket.abstract_models import AbstractLine
from oscarbluelight.mixins import BluelightBasketLineMixin

class Line(BluelightBasketLineMixin, AbstractLine):
    pass

from oscar.apps.basket.models import *  # noqa
```

## Usage

After installation, the new functionality will show up in the Oscar
dashboard under the Offers menu.

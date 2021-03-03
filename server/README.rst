===============================
Django Oscar Bluelight Specials
===============================

|  |license| |kit| |format|

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
    from oscarbluelight.defaults import *  # Needed so that Bluelight's views show up in the dashboard

Add Bluelight to your installed apps (replacing the equivalent Django Oscar apps). The top-level ``oscarbluelight`` app must be defined before the ``oscar`` app—if it isn't Django will not correctly find the Bluelight's templates.::

    INSTALLED_APPS = [
        ...
        # Bluelight. Must come before `django-oscar` so that template inheritance / overrides work correctly.
        'oscarbluelight',
        'django_pgviews',

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

Fork the basket application in your project and add ``BluelightBasketMixin`` as a parent class of the ``Line`` model.::

    from oscar.apps.basket.abstract_models import AbstractLine
    from oscarbluelight.mixins import BluelightBasketLineMixin

    class Line(BluelightBasketLineMixin, AbstractLine):
        pass

    from oscar.apps.basket.models import *  # noqa


Usage
=====

After installation, the new functionality will show up in the Oscar dashboard under the Offers menu.


Changelog
=========

4.0.0
------------------
- Oscar 3.0 Compatibility
- Add checkbox for excluding offer from cosmetic pricing

3.0.1
-------------------
- Improve performance of the "Add Products to Range" functionality in the dashboard by utilizing batch inserts.

3.0.0
------------------
- Use Postgres materialized views to improve performance of querying for products in a range.

2.0.0
------------------
- Support django-oscar 2.1

1.0.0
------------------
- Add improved reporting formats for offers and vouchers.

0.14.1
------------------
- Fix bug in CompoundBenefit which caused lines to not be properly consumed by a condition if the last-to-be-applied child benefit didn't trigger a discount.

0.14.0
------------------
- Add support for django-oscar 2.x.
- Drop support for django-oscar 1.x.

0.13.0
------------------
- Internationalization
- Feature: Compound Benefits. Allows applying more than one benefit with a single offer.
- Improve performance of Range.contains_product by utilizing Redis SETs. Requires Redis caching on the Django site

0.12.0
------------------
- Improve UI of the offer group dashboard view.
- Improve checkout performance by tuning the update query in Offer.record_usage.
- Alter behavior of MultibuyDiscountBenefit. Not discounts the second-most expensive product, rather than the cheapest product.
- Remove now-unused cosmetic-pricing settings.

0.11.1
------------------
- Fix bug with effective price.

0.11.0
------------------
- Add support for adding images to Offers and Vouchers.
- Add support for Python 3.7.
- Add support for Django 2.1.

0.10.0
------------------
- Add flag to offer result objects to allow flagging a result as hidden in the UI. Doesn't functionally affect anything other than adding the boolean flag property.
- Bugfix for clearing products from range cache

0.9.0
------------------
- Add support for Oscar 1.6 and Django 2.0.
    - Due to the write of the offer's system in Oscar 1.6, this release drops support for Oscar 1.5.

0.8.7
------------------
- Fix exception thrown when editing a voucher
- Fix broken Webpack build

0.8.6
------------------
- Improve performance of offer application by caching the results of ``Range.contains_product`` and ``Range.contains``.

0.8.5
------------------
- Improve performance of cosmetic price application by using ``select_related``.

0.8.4
------------------
- Fix Django 2.0 Deprecation warnings.

0.8.3
------------------
- Fix bug preventing saving an Offer's short name in the dashboard.

0.8.2
------------------
- Fix method signature bug in several shipping benefits.

0.8.1
------------------
- Adds support for Django 1.11 and Oscar 1.5

0.8.0
------------------
- Add Concept of System Offer Groups.
    - System Offer Groups are standard offer groups, but are automatically created and are ensured to always exist. They can not, therefore, be created or deleted via the dashboard UI. They are lazy-created by referencing them in code using the ``oscarbluelight.offer.groups.register_system_offer_group(slug='foo')`` function.
    - Along with this functionality comes the addition of offer and group related signals which can be used to perform actions at specific points in time during offer group application. For example you could create a system offer group for offers which should be applied only after taxes have been calculated. Then you could use the ``pre_offer_group_apply`` signal to perform tax calculation on a basket directly before the offer group is applied.

0.7.1
------------------
- Fix exception in dashboard when adding compound conditions

0.7.0
------------------
- Fix bug related to conditions consuming basket lines when the condition range differed from the benefit range.
- Run model validation before applying benefits to a basket. Results in better error reporting of invalid but difficult to enforce data.
- Start to rebuild OfferGroup dashboard view as a React application.
    - Currently just recreates existing functionality using React and an API endpoint.
    - Next release will include drag-and-drop priority sorting of offers, vouchers, and offer groups.

0.6.1
------------------
- Drop Django 1.9 support.
- In offer group list, dim inactive offers and vouchers.
- List related vouchers on benefit and condition edit pages.
- Limit orders displayed on voucher stats.
- Start testing against Django 1.11 and Oscar 1.5rc1:
    - Fix issue with Voucher ordering when doing a select_for_update.
    - Fix Oscar 1.5 issue with conditionaloffer_set vs offers related name.
    - Fix Oscar 1.5 issue with basket.Line.line_tax.
    - Upgrade sandbox to Oscar 1.5.
- Add new field to ConditionalOffer: short_name
- Make OfferApplications ordered

0.6.0
------------------
- Add concept of Offer groups.
    - This makes it possible to create promotions which overlap on line items.
- Add API for determining why a line was discounted.

0.5.4
------------------
- Improve unit testing with tox.

0.5.3
------------------
- Upgrade test dependencies.

0.5.2
------------------
- Upgraded to ``versiontag`` 1.2.0.

0.5.1
------------------
- Fixed bug where voucher condition range was always set to be equal to the benefit range.

0.5.0
------------------
- Create custom subclasses of all built-in Oscar conditions and Benefits
    - Eliminates need for monkey-patching the ``Condition.consume_items`` method.
    - Adds migration to change all row's proxy_class from ``oscar.apps.offer.FOOBAR`` to ``oscarbluelight.offer.FOOBAR``.
- Change behavior of ``FixedPriceBenefit`` to be more logical.
    - Uses the benefit's assigned range instead of the condition's range.
    - Respects the ``max_affected_items`` setting.
- Improved dashboard form validation using polymorphic ``_clean`` methods on benefits and conditions.
- Disallow deleting a range when a benefit or a condition depends on it.
- If a benefit or condition's proxy_class isn't a proxy_model, automatically create the row in the subclass's table.

0.4.1
------------------
- Fixed several exceptions throw in dashboard views when a voucher had no offers linked to it.

0.4.0
------------------
- Dashboard:
    - Separate vouchers form offers in benefits and conditions lists
    - Add condition field to voucher form. Allows creating more complex vouchers, such as those that require specific items in the basket.
    - Add priority field to vouchers and offers forms. Display priority field in detail and list fields.
    - Add offer restrictions fields to voucher form.
- Performance:
    - Move child code creation and updating background task with Celery.

0.3.1
------------------
- Use correct transaction.atomic syntax in voucher creation.
- Fix validation of voucher name and code when child codes exist.
- Set max_length to 128 on name field of voucher form, to match model.

0.3.0
------------------
- Makes it possible to selectively apply offers to specific groups of users (using django.auth.contrib.models.Group).
- Adds custom dashboard screens for managing offer / voucher benefits.

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

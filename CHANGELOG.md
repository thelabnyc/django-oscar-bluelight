## v5.13.0 (2026-02-10)

### Feat

- widen django-tasks support to >=0.7.0 for Wagtail compatibility

### Fix

- **deps**: update dependency thelabdb to >=0.7.0

## v5.12.1 (2026-02-02)

### Fix

- Unable to Access Second Page of Offers

## v5.12.0 (2026-01-30)

### Feat

- support Python 3.14

### Fix

- avoid voucher code space exhaustion by pre-filling start_index
- optimize voucher child creation and uniqueness checks
- **deps**: update dependency django-tasks to >=0.11.0,<0.11.1
- **deps**: update dependency celery to >=5.6.2
- **deps**: update dependency celery to >=5.6.1
- **deps**: update dependency thelabdb to >=0.6.1
- **deps**: update dependency django-tasks to >=0.10.0,<0.10.1
- **deps**: update dependency django to >=5.2
- **deps**: update dependency django to >=4.2.27
- **deps**: update dependency thelabdb to >=0.6.0
- **deps**: update dependency celery to >=5.6.0
- override get_applicable_lines() in CompoundCondition

## v5.11.2 (2025-11-19)

### Fix

- **deps**: update dependency django-oscar to >=4.1,<4.2
- **deps**: update dependency django-tasks to >=0.9.0,<0.9.1
- **deps**: update dependency django-tasks to >=0.9.0,<0.9.1
- **deps**: update dependency thelabdb to >=0.5.1
- **deps**: update dependency django-tasks to >=0.8.1
- **deps**: update dependency djangorestframework to >=3.16.1,<4
- **deps**: update dependency celery to >=5.5.3
- prevent renovate from pointing all URLs at gitlab

## v5.11.1 (2025-08-18)

### Fix

- satisfying_lines tracking code being reset due to how condition proxies work (#29620)

## v5.11.0 (2025-08-18)

### Feat

- add system for tracking while lines caused a condition to be satisfied (#29620)
- add pluggable line filter strategy system for offer benefits (#29620)

### Fix

- fix bug where consumption of individual offers was not being tracked correctly within BluelightLineOfferConsumer (#29620)
- patch bug where zero cost basket lines were not consumed by conditions (#29620)
- docker file fixups for local dev

## v5.10.2 (2025-07-16)

### Fix

- fix E005 django check error

## v5.10.1 (2025-07-14)

### Fix

- isort
- prevent duplicated calls to recalculate_offer_application_totals (#30381)

### Refactor

- migrate black/flake8 -> ruff
- migrate from poetry -> uv

## v5.10.0 (2025-06-20)

### Feat

- support both celery (default) and django-tasks as task queue backends (#29527)
- test against django 5.2

### Fix

- update docker image tag format
- **deps**: update dependency django-oscar to >=4.0,<4.1
- update tests for oscar 4.0
- **deps**: update dependency celery to ^5.5.1
- **deps**: update dependency thelabdb to >=0.5.0
- **deps**: update dependency django-oscar to >=3.2.6,<4.1
- **deps**: update dependency celery to ^5.5.0

## v5.9.1 (2025-04-03)

### Fix

- set correct repo urls

## v5.9.0 (2025-04-03)

### Feat

- add support for Django 5.0

### Fix

- **deps**: update react monorepo to ^19.1.0
- **deps**: update dependency djangorestframework to ^3.16.0

### Refactor

- add pyupgrade / django-upgrade precommit hooks

## v5.8.3 (2025-03-21)

### Fix

- missing kwarg in shipping benefits

## v5.8.2 (2025-03-21)

### Fix

- voucher name types
- TypeError: type 'Field' is not subscriptable
- use NullCharField from thelabdb

## v5.8.1 (2025-03-17)

### Fix

- **deps**: update dependency thelabdb to ^0.3.0
- **deps**: update dependency superagent to ^10.2.0
- **deps**: update dependency django to ^4.2.20
- **deps**: update dependency core-js to ^3.41.0

## v5.8.0 (2025-02-13)

### Feat

- add pagination to items listed under each condition in Conditions dashboard view

### Fix

- **deps**: update dependency django to ^4.2.19

## v5.7.1 (2025-01-21)

### Fix

- drop Python 3.11
- **deps**: update dependency thelabdb to ^0.2.0
- **deps**: update dependency django to ^4.2.18
- **deps**: update react monorepo to v19

## v5.7.0 (2025-01-14)

### Feat

- add type annotations
- add product search by name, UPC, and SKU within a product range

### Fix

- **deps**: update dependency core-js to ^3.40.0

## v5.6.0 (2024-12-23)

### Feat

- add loading state to offer groups load more button (#25405)
- implement pagination for offers within each offer group on the Offer Groups dashboard view (#25405)
- Add offer group filter to offer dashboard view and limit the number of offers displayed for an offer group (#25405)

### Fix

- **deps**: update dependency django to ^4.2.17
- **deps**: update dependency core-js to ^3.39.0
- **deps**: update dependency tslib to ^2.8.1
- **deps**: update dependency superagent to ^10.1.1
- **deps**: update dependency tslib to ^2.8.0
- remove @babel/plugin-syntax-dynamic-import plugin

## v5.5.15 (2024-09-25)

### Fix

- **deps**: update dependency django-oscar to v3.2.5
- pin django-oscar version due to breaking changes in patch versions
- **deps**: update dependency superagent to v10
- **deps**: update dependency django to ^4.2.16
- **deps**: update dependency thelabdb to ^0.1.2

### Perf

- improve performance of RangeProductSet materialized view SQL

## v5.5.14 (2024-08-31)

### Fix

- add missing migration
- fix behavior of bulk add/exclude forms in RangeProductListView

## v5.5.13 (2024-08-28)

### Fix

- resolve NoReverseMatch error for `voucher-list-children`
- **deps**: update dependency tslib to ^2.7.0
- **deps**: update dependency core-js to ^3.38.1

## v5.5.12 (2024-08-12)

### Fix

- **deps**: update dependency django to ^4.2.15

### Perf

- introduce update_children arg in the child creation method

## v5.5.12b0 (2024-08-08)

### Fix

- **deps**: update dependency core-js to ^3.38.0
- **deps**: update dependency django to ^4.2.14
- **deps**: update dependency regenerator-runtime to ^0.14.1
- **deps**: update dependency django to ^4.2.13
- **deps**: update dependency core-js to ^3.37.1
- **deps**: update dependency classnames to ^2.5.1
- **deps**: update dependency djangorestframework to v3.15.2
- **deps**: update dependency superagent to v8.1.2
- **deps**: update dependency regenerator-runtime to ^0.14.0
- **deps**: update dependency celery to v5.4.0
- **deps**: update dependency core-js to v3.37.1
- **deps**: update dependency classnames to v2.5.1
- **deps**: update dependency django to v4.2.13
- **deps**: update dependency djangorestframework to v3.15.1

## v5.5.11

- Fix offer pagination bugs introduced by 5.5.10 (see !87).

## v5.5.10

- Improve offer select performance on voucher creation screen.

## v5.5.9

- Improve query performance of child-voucher creation-date table.

## v5.5.8

- Improve query performance for copying parent-to-child offers relationship
- Fix order status bug in get_recalculate_offer_application_totals_sql

## v5.5.7

- Fix compatibility with Oscar 3.2.3.

## v5.5.6

- Tweak `Voucher._create_child_batch` so that batch size does not exceed Postgres limit of 65535 query params

## v5.5.5

- Improve performance of child code additions

## v5.5.4

- Add support for psycopg

## v5.5.3

- Fix bug when basket line unit_effective_price is None.

## v5.5.2

- Fix bug where dashboard range form error messages were not consistent with the actual DB state.

## v5.5.1

- Fix performance regression in Voucher.\_get_child_code_batch

## v5.5.0

- Add conjunction type to CompoundBenefits
- Add support for django-oscar 3.2.2
- Add support for django 4.2

## v5.4.0

- Add rules framework to allow library consumers to change how vouchers are determined to be available or not.
- Add functionality for recalculating offer application totals based on OrderDiscount models. This allows correcting voucher discount stats to account for canceled orders.
- Redesign RangeProductSet view updating to improve web request performance (at the cost of allowing the view to be slightly out of date).
- Fix issue where a voucher is applied multiple times when it contains multiple offers.
- Allow HiddenPostOrderAction benefits to be combined with other benefit types.
- Improve descriptions of fixed price benefits.

## v5.3.0

- Add new system for obtaining structured data regarding offer upsell messages
- Add `BLUELIGHT_IGNORED_ORDER_STATUSES`, ignore voucher usage on orders with those statuses

## v5.2.4
- Change `DEFAULT_AUTO_FIELD` to `BigAutoField`, migrate `Voucher_offers` through table.

## v5.2.3

- Fix bug where Voucher.\_create_child returns the unsaved voucher object instead of the saved version.

## v5.2.2

- Fix performance issues with creating / updating large numbers of child voucher codes.

## v5.2.1

- Fix 500 error in dashboard when saving offer directly from form step 1.

## v5.2.0

- Add created date filtering to Voucher child code export view.

## v5.1.3

- Fix performance issue in VoucherStatsView when a code had a large number of child codes.

## v5.1.2

- Revert change to `CREATE OR REPLACE TRIGGER` from `r5.1.1` since this syntax is only supported in PostgreSQL 14.

## v5.1.1

- Reduce opportunities for deadlocks while updating PostgresSQL views and triggers.

## v5.1.0

-   Add new `max_discount` field to Benefit models, to allow capping the total discount granted by a benefit within a single application. Primary intended use case is for capping the discount granted by a compound benefits, when its child benefits could, in some product combinations, exceed the desired discount.
-   Convert README from reStructuredText to Markdown.
-   Fix performance issues related to vouchers with large numbers if children.

## v5.0.1

-   Remove duplicate `offer_type` field from offer form.

## v5.0.0

-   Oscar 3.1 compatibility
-   Drops Oscar 3.0 compatibility (due to 3.1's significant changes to offers / vouchers).
-   Fix bug in Offer Restrictions form which always reset voucher-type
    offers to site-type offers.
-   Add new "Fixed Price Per Item" benefit type

## v4.1.0

-   Add new dashboard view to view and delete voucher child codes.
-   Tweak voucher form to allow creating custom child codes on initial
    voucher creation.

## v4.0.0

-   Oscar 3.0 Compatibility
-   Add checkbox for excluding offer from cosmetic pricing

## v3.0.1

-   Improve performance of the \"Add Products to Range\" functionality
    in the dashboard by utilizing batch inserts.

## v3.0.0

-   Use Postgres materialized views to improve performance of querying
    for products in a range.

## v2.0.0

-   Support django-oscar 2.1

## v1.0.0

-   Add improved reporting formats for offers and vouchers.

## v0.14.1

-   Fix bug in CompoundBenefit which caused lines to not be properly
    consumed by a condition if the last-to-be-applied child benefit
    didn't trigger a discount.

## v0.14.0

-   Add support for django-oscar 2.x.
-   Drop support for django-oscar 1.x.

## v0.13.0

-   Internationalization
-   Feature: Compound Benefits. Allows applying more than one benefit
    with a single offer.
-   Improve performance of Range.contains_product by utilizing Redis
    SETs. Requires Redis caching on the Django site

## v0.12.0

-   Improve UI of the offer group dashboard view.
-   Improve checkout performance by tuning the update query in
    Offer.record_usage.
-   Alter behavior of MultibuyDiscountBenefit. Not discounts the
    second-most expensive product, rather than the cheapest product.
-   Remove now-unused cosmetic-pricing settings.

## v0.11.1

-   Fix bug with effective price.

## v0.11.0

-   Add support for adding images to Offers and Vouchers.
-   Add support for Python 3.7.
-   Add support for Django 2.1.

## v0.10.0

-   Add flag to offer result objects to allow flagging a result as
    hidden in the UI. Doesn't functionally affect anything other than
    adding the boolean flag property.
-   Bugfix for clearing products from range cache

## v0.9.0

-   Add support for Oscar 1.6 and Django 2.0.
    -   Due to the write of the offer's system in Oscar 1.6, this
        release drops support for Oscar 1.5.

## v0.8.7

-   Fix exception thrown when editing a voucher
-   Fix broken Webpack build

## v0.8.6

-   Improve performance of offer application by caching the results of
    `Range.contains_product` and `Range.contains`.

## v0.8.5

-   Improve performance of cosmetic price application by using
    `select_related`.

## v0.8.4

-   Fix Django 2.0 Deprecation warnings.

## v0.8.3

-   Fix bug preventing saving an Offer's short name in the dashboard.

## v0.8.2

-   Fix method signature bug in several shipping benefits.

## v0.8.1

-   Adds support for Django 1.11 and Oscar 1.5

## v0.8.0

-   Add Concept of System Offer Groups.
    -   System Offer Groups are standard offer groups, but are
        automatically created and are ensured to always exist. They
        can not, therefore, be created or deleted via the dashboard
        UI. They are lazy-created by referencing them in code using
        the
        `oscarbluelight.offer.groups.register_system_offer_group(slug='foo')`
        function. - Along with this functionality comes the addition of offer
        and group related signals which can be used to perform
        actions at specific points in time during offer group
        application. For example you could create a system offer
        group for offers which should be applied only after taxes
        have been calculated. Then you could use the
        `pre_offer_group_apply` signal to perform tax calculation on
        a basket directly before the offer group is applied.

## v0.7.1

-   Fix exception in dashboard when adding compound conditions

## v0.7.0

-   Fix bug related to conditions consuming basket lines when the
    condition range differed from the benefit range.
-   Run model validation before applying benefits to a basket. Results
    in better error reporting of invalid but difficult to enforce data.
-   Start to rebuild OfferGroup dashboard view as a React application.
    -   Currently just recreates existing functionality using React
        and an API endpoint. - Next release will include drag-and-drop priority sorting of
        offers, vouchers, and offer groups.

## v0.6.1

-   Drop Django 1.9 support.
-   In offer group list, dim inactive offers and vouchers.
-   List related vouchers on benefit and condition edit pages.
-   Limit orders displayed on voucher stats.
-   Start testing against Django 1.11 and Oscar 1.5rc1:
    -   Fix issue with Voucher ordering when doing a
        select_for_update. - Fix Oscar 1.5 issue with conditionaloffer_set vs offers
        related name. - Fix Oscar 1.5 issue with basket.Line.line_tax. - Upgrade sandbox to Oscar 1.5.
-   Add new field to ConditionalOffer: short_name
-   Make OfferApplications ordered

## v0.6.0

-   Add concept of Offer groups.
    -   This makes it possible to create promotions which overlap on
        line items.
-   Add API for determining why a line was discounted.

## v0.5.4

-   Improve unit testing with tox.

## v0.5.3

-   Upgrade test dependencies.

## v0.5.2

-   Upgraded to `versiontag` 1.2.0.

## v0.5.1

-   Fixed bug where voucher condition range was always set to be equal
    to the benefit range.

## v0.5.0

-   Create custom subclasses of all built-in Oscar conditions and Benefits
    -   Eliminates need for monkey-patching the
        `Condition.consume_items` method. - Adds migration to change all row's proxy_class from
        `oscar.apps.offer.FOOBAR` to `oscarbluelight.offer.FOOBAR`.
-   Change behavior of `FixedPriceBenefit` to be more logical.
    -   Uses the benefit's assigned range instead of the
        condition's range. - Respects the `max_affected_items` setting.
-   Improved dashboard form validation using polymorphic `_clean`
    methods on benefits and conditions.
-   Disallow deleting a range when a benefit or a condition depends on
    it.
-   If a benefit or condition's proxy_class isn't a proxy_model,
    automatically create the row in the subclass's table.

## v0.4.1

-   Fixed several exceptions throw in dashboard views when a voucher had
    no offers linked to it.

## v0.4.0

-   Dashboard:
    -   Separate vouchers form offers in benefits and conditions
        lists - Add condition field to voucher form. Allows creating more
        complex vouchers, such as those that require specific items
        in the basket. - Add priority field to vouchers and offers forms. Display
        priority field in detail and list fields. - Add offer restrictions fields to voucher form.
-   Performance:
    -   Move child code creation and updating background task with
        Celery.

## v0.3.1

-   Use correct transaction.atomic syntax in voucher creation.
-   Fix validation of voucher name and code when child codes exist.
-   Set max_length to 128 on name field of voucher form, to match model.

## v0.3.0

-   Makes it possible to selectively apply offers to specific groups of
    users (using django.auth.contrib.models.Group).
-   Adds custom dashboard screens for managing offer / voucher benefits.

## v0.2.2

-   Fix bug preventing Voucher.groups form field from being blank

## v0.2.1

-   Fix bug the excluded templates from package.

## v0.2.0

-   Renamed package to [oscarbluelight]{.title-ref} to have consistent
    naming with other Oscar projects.

## v0.1.1

-   Fix bug the excluded templates from package.

## v0.1.0

-   Initial release.

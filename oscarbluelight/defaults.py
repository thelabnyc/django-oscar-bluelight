from django.utils.translation import ugettext_lazy as _
from oscar.defaults import OSCAR_DASHBOARD_NAVIGATION


def insert_nav_item(after_name, label, url_name):
    new_entry = {
        'label': label,
        'url_name': url_name,
    }
    for i, section in enumerate(OSCAR_DASHBOARD_NAVIGATION):
        for j, entry in enumerate(section.get('children', [])):
            if entry.get('url_name') == after_name:
                OSCAR_DASHBOARD_NAVIGATION[i]['children'].insert(j + 1, new_entry)


insert_nav_item('dashboard:offer-list', _('Benefits'), 'dashboard:benefit-list')
insert_nav_item('dashboard:benefit-list', _('Conditions'), 'dashboard:condition-list')



BLUELIGHT_BENEFIT_CLASSES = [
    ('oscar.apps.offer.benefits.PercentageDiscountBenefit', _("Discount is a percentage off of the product's value")),
    ('oscar.apps.offer.benefits.AbsoluteDiscountBenefit', _("Discount is a fixed amount off of the product's value")),
    ('oscar.apps.offer.benefits.MultibuyDiscountBenefit', _("Discount is to give the cheapest product for free")),
    ('oscar.apps.offer.benefits.FixedPriceBenefit', _("Get the products that meet the condition for a fixed price")),
    ('oscar.apps.offer.benefits.ShippingAbsoluteDiscountBenefit', _("Discount is a fixed amount of the shipping cost")),
    ('oscar.apps.offer.benefits.ShippingFixedPriceBenefit', _("Get shipping for a fixed price")),
    ('oscar.apps.offer.benefits.ShippingPercentageDiscountBenefit', _("Discount is a percentage off of the shipping cost")),
]


BLUELIGHT_CONDITION_CLASSES = [
    ('oscar.apps.offer.conditions.CountCondition', _("Depends on number of items in basket that are in condition range")),
    ('oscar.apps.offer.conditions.ValueCondition', _("Depends on value of items in basket that are in condition range")),
    ('oscar.apps.offer.conditions.CoverageCondition', _("Needs to contain a set number of DISTINCT items from the condition range")),
]

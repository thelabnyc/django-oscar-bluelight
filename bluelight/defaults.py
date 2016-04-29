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


insert_nav_item('dashboard:offer-list', _('Conditions'), 'dashboard:condition-list')

from django.utils.translation import gettext_lazy as _
from .applicator import Applicator  # NOQA
from .constants import Conjunction


def human_readable_conjoin(conjunction, strings, empty=None):
    labels = {
        Conjunction.AND: _(" and "),
        Conjunction.OR: _(" or "),
    }
    strings = list(strings)
    if len(strings) <= 0 and empty is not None:
        return empty
    return labels[conjunction].join(strings)

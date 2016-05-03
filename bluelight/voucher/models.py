from django.db import models
from django.utils.translation import ugettext_lazy as _
from oscar.apps.voucher.abstract_models import AbstractVoucher


class Voucher(AbstractVoucher):
    limit_usage_by_group = models.BooleanField(_("Limit usage to selected user groups"), default=False)
    groups = models.ManyToManyField('auth.Group', verbose_name=_("User Groups"))

    def is_available_to_user(self, user=None):
        if self.limit_usage_by_group:
            message = _("This voucher is only available to selected users")
            if not user:
                return False, message
            group_ids = set(g.id for g in self.groups.all())
            member_ids = set(g.id for g in user.groups.all())
            is_member = group_ids & member_ids
            if not is_member:
                return False, message
        return super().is_available_to_user(user)


from oscar.apps.voucher.models import *  # noqa

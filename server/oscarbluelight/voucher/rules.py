from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.utils.translation import gettext_lazy as _

from .models import Voucher

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise


class VoucherRule:
    _message: StrOrPromise = ""
    _desc: StrOrPromise = _("Check if the voucher %(voucher_name)s violates the rule")

    def __init__(
        self,
        voucher: Voucher,
        user: AnonymousUser | User | None = None,
    ):
        self.voucher = voucher
        self.user = user

    def is_obeyed_by_user(self) -> bool:
        return True

    def get_msg_text(self) -> StrOrPromise:
        context = self.get_summary_tmpl_context()
        return "" if self.is_obeyed_by_user() else self.get_msg_tmpl() % context

    def get_desc_text(self) -> StrOrPromise:
        context = self.get_summary_tmpl_context()
        return self.get_desc_tmpl() % context

    def get_summary(self) -> StrOrPromise:
        return _("%(description)s: %(message)s") % {
            "description": self.get_desc_text(),
            "message": self.get_msg_text(),
        }

    def get_summary_tmpl_context(self) -> dict[str, StrOrPromise]:
        return {
            "voucher_name": self.voucher.name,
        }

    def get_msg_tmpl(self) -> StrOrPromise:
        return self._message

    def get_desc_tmpl(self) -> StrOrPromise:
        return self._desc


class VoucherHasChildrenRule(VoucherRule):
    _message = _("This voucher is not available")
    _desc = _("Check if the voucher %(voucher_name)s has children")

    def is_obeyed_by_user(self) -> bool:
        ret = super().is_obeyed_by_user()
        # Parent vouchers can not be used directly
        if self.voucher.list_children().exists():
            return False
        return ret


class VoucherSuspendedRule(VoucherRule):
    _message = _("This voucher is currently inactive")
    _desc = _("Check if the voucher %(voucher_name)s is suspended")

    def is_obeyed_by_user(self) -> bool:
        ret = super().is_obeyed_by_user()
        if self.voucher.is_suspended:
            return False
        return ret


class VoucherLimitUsageByGroupRule(VoucherRule):
    _message = _("This voucher is only available to selected users")
    _desc = _(
        "Check if limit_usage_by_group is set for the voucher %(voucher_name)s and user is not in one of the selected groups"
    )

    def is_obeyed_by_user(self) -> bool:
        ret = super().is_obeyed_by_user()
        # Enforce user group whitelisting
        if self.voucher.limit_usage_by_group:
            if not self.user:
                return False
            group_ids = {g.id for g in self.voucher.groups.all()}
            member_ids = {g.id for g in self.user.groups.all()}
            is_member = len(group_ids & member_ids) > 0
            if not is_member:
                return False
        return ret


class VoucherSingleUseRule(VoucherRule):
    _message = _("This voucher has already been used")
    _desc = _(
        "Check if the voucher %(voucher_name)s is single use and has already been used"
    )

    def is_obeyed_by_user(self) -> bool:
        ret = super().is_obeyed_by_user()
        if self.voucher.usage == Voucher.SINGLE_USE:
            # Ignore statuses in BLUELIGHT_IGNORED_ORDER_STATUSES
            is_available = not self.voucher.applications.exclude(
                order__status__in=settings.BLUELIGHT_IGNORED_ORDER_STATUSES
            ).exists()
            return is_available
        return ret


class VoucherSingleUsePerCustomerRule(VoucherRule):
    _message = _("You have already used this voucher in a previous order")
    _desc = _(
        "Check if the voucher %(voucher_name)s is single use per customer and customer has already used it"
    )

    def is_obeyed_by_user(self) -> bool:
        ret = super().is_obeyed_by_user()
        if self.voucher.usage == Voucher.ONCE_PER_CUSTOMER:
            authd_user: User | None = (
                self.user if self.user and self.user.is_authenticated else None
            )
            if authd_user:
                # Ignore statuses in BLUELIGHT_IGNORED_ORDER_STATUSES
                is_available = (
                    not self.voucher.applications.exclude(
                        order__status__in=settings.BLUELIGHT_IGNORED_ORDER_STATUSES
                    )
                    .filter(voucher=self.voucher, user=authd_user)
                    .exists()
                )
                return is_available
            self._message = _("This voucher is only available to signed in users")
            return False
        return ret


__all__ = [
    "VoucherHasChildrenRule",
    "VoucherSuspendedRule",
    "VoucherLimitUsageByGroupRule",
    "VoucherSingleUseRule",
    "VoucherSingleUsePerCustomerRule",
]

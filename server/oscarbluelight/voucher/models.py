from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Self
import time

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.db import connection, models, transaction
from django.db.models.base import ModelBase
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from oscar.apps.voucher.abstract_models import AbstractVoucher
from thelabdb.fields import NullCharField

from ..offer.models import Benefit, Condition, OfferGroup
from . import sql, tasks

if TYPE_CHECKING:
    from django_stubs_ext import StrOrPromise
    from oscar.apps.order.models import Order


class VoucherQuerySet(models.QuerySet["Voucher"]):
    def exclude_children(self) -> Self:
        return self.filter(parent=None)

    def select_for_update(
        self,
        nowait: bool = False,
        skip_locked: bool = False,
        of: Sequence[str] = (),
        no_key: bool = False,
    ) -> Self:
        """
        To do a select_for_updarte, we have to reset the query ordering so that it doesn't try to do
        outer joins to the ConditionalOffer and OfferGroup tables.
        """
        qs = self.order_by("pk")
        return models.QuerySet.select_for_update(qs, nowait, skip_locked, of, no_key)


class VoucherManager(models.Manager["Voucher"]):
    def get_queryset(self) -> VoucherQuerySet:
        return VoucherQuerySet(self.model, using=self._db)

    def exclude_children(self) -> VoucherQuerySet:
        return self.get_queryset().exclude_children()


class Voucher(AbstractVoucher):
    name = NullCharField(
        _("Name"),
        max_length=128,
        unique=True,
        help_text=_(
            "This will be shown in the checkout and basket once the voucher is entered"
        ),
    )
    parent = models.ForeignKey(
        "self",
        verbose_name=_("Parent Voucher"),
        related_name="children",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    limit_usage_by_group = models.BooleanField(
        _("Limit usage to selected user groups"), default=False
    )
    groups = models.ManyToManyField(
        "auth.Group", verbose_name=_("User Groups"), blank=True
    )
    OPEN, SUSPENDED = "Open", "Suspended"
    status = models.CharField(_("Status"), max_length=64, default=OPEN)

    objects = VoucherManager()

    class Meta:
        base_manager_name = "objects"
        ordering = ("-offers__offer_group__priority", "-offers__priority", "pk")

    @classmethod
    def from_db(
        cls,
        db: str | None,
        field_names: Collection[str],
        values: Collection[Any],
    ) -> Voucher:
        instance = super().from_db(db, field_names, values)

        # Child codes always get the parent's name
        def _get_parent_name() -> StrOrPromise | None:
            return instance.parent.name if instance.parent else None

        if instance.parent_id:
            parent_name = cache.get_or_set(
                instance._get_parent_name_cache_key(), _get_parent_name, 60
            )
            instance.name = parent_name or ""
        return instance

    def _get_parent_name_cache_key(self, parent_id: int | None = None) -> str:
        if parent_id is None:
            parent_id = self.parent_id
        return f"oscarbluelight.Voucher.parent_name.{parent_id}"

    def is_active(self, test_datetime: datetime | None = None) -> bool:
        ret = super().is_active(test_datetime)
        if self.is_suspended:
            return False
        return ret

    @property
    def offer_group(self) -> OfferGroup | None:
        offer = self.offers.first()
        return offer.offer_group if offer else None

    @property
    def priority(self) -> int:
        offer = self.offers.first()
        return offer.priority if offer else 0

    @property
    def condition(self) -> Condition | None:
        offer = self.offers.first()
        return offer.condition if offer else None

    @property
    def benefit(self) -> Benefit | None:
        offer = self.offers.first()
        return offer.benefit if offer else None

    @property
    def is_open(self) -> bool:
        return self.status == self.OPEN

    @property
    def is_suspended(self) -> bool:
        return self.status == self.SUSPENDED

    def suspend(self) -> None:
        self.status = self.SUSPENDED
        self.save()

    suspend.alters_data = True  # type:ignore[attr-defined]

    def unsuspend(self) -> None:
        self.status = self.OPEN
        self.save()

    unsuspend.alters_data = True  # type:ignore[attr-defined]

    def is_available_to_user(
        self,
        user: User | AnonymousUser | None = None,
    ) -> tuple[bool, str]:
        is_available, message = True, ""
        rule_classes = getattr(settings, "BLUELIGHT_VOUCHER_AVAILABILITY_RULES", [])
        for path, desc in rule_classes:
            rule_cls = import_string(path)
            applied_rule = rule_cls(self, user)
            if not applied_rule.is_obeyed_by_user():
                is_available = False
                message = applied_rule.get_msg_text()
                break
        return is_available, message

    def list_children(self) -> models.QuerySet[Voucher]:
        return self.children.select_related("parent").all()

    @transaction.atomic
    def create_children(
        self,
        auto_generate_count: int = 0,
        custom_codes: Sequence[Any] = [],
    ) -> tuple[list[StrOrPromise], int]:
        if self.parent is not None:
            raise RuntimeError(
                _(
                    "Can not create children for a child voucher. Nesting should only be 1 level."
                )
            )
        if not self.id:
            self.save()
        errors = []
        success_count = 0
        # Generate auto codes
        auto_gen_codes = self._get_child_code_batch(auto_generate_count)
        # Update newly created child vouchers only when calling `_create_child_batch` for the last time.
        success_count += len(
            self._create_child_batch(auto_gen_codes, update_children=False)
        )
        # Save manual/custom codes
        custom_code_successes = self._create_child_batch(
            custom_codes, update_children=False
        )
        success_count += len(custom_code_successes)
        custom_code_failures = set(custom_codes) - custom_code_successes
        for code in sorted(list(custom_code_failures)):
            errors.append(
                _("Could not create code “%s” because it already exists.") % code
            )
        return errors, success_count

    @transaction.atomic
    def update_children(self) -> None:
        """
        If logic here changes, make sure to also update the single-child update
        version (`Voucher._update_child`)
        """
        # Wipe the parent name cache
        cache.delete(self._get_parent_name_cache_key(self.pk))
        # Batch update all the children. Uses raw SQL since this is the most
        # efficient way to do this for vouchers with large numbers (e.g. millions)
        # of child codes.
        with connection.cursor() as cursor:
            params = {
                "parent_id": self.pk,
            }
            queries = [
                # Copy parent metadata to all children
                sql.get_update_children_meta_sql(Voucher),
                # Copy offers m2m relationship from parent to all children
                sql.get_insupd_children_offers_sql(Voucher),
                sql.get_prune_children_offers_sql(Voucher),
                # Copy groups m2m relationship from parent to all children
                sql.get_insupd_children_groups_sql(Voucher),
                sql.get_prune_children_groups_sql(Voucher),
            ]
            for query in queries:
                cursor.execute(query, params)

    def save(
        self,
        update_children: bool = True,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        # Child codes use the parent's name and always store Null for their own name
        _orig_name = self.name
        if self.parent:
            self.name = ""
            cache.delete(self._get_parent_name_cache_key(self.parent_id))
        else:
            cache.delete(self._get_parent_name_cache_key(self.pk))
        # Save the object
        rc = super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
        # Update children?
        if update_children:
            tasks.update_child_vouchers.enqueue(self.id)
        # Restore the original name
        if self.parent:
            self.name = _orig_name
        return rc

    @transaction.atomic
    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        offers = self.offers.all()
        rc = super().delete(*args, **kwargs)
        for offer in offers:
            # Delete the benefit and offer, since they're auto created
            condition = offer.condition
            offer.delete()
            if condition.offers.count() == 0:
                condition.delete()
        return rc

    def record_usage(self, order: Order, user: User, *args: Any, **kwargs: Any) -> None:
        if self.parent:
            if user.is_authenticated:
                self.parent.applications.create(
                    voucher=self.parent, order=order, user=user
                )
            else:
                self.parent.applications.create(voucher=self.parent, order=order)
            self.parent.num_orders += 1
            self.parent.save(update_children=False)

        return super().record_usage(order, user, *args, **kwargs)

    record_usage.alters_data = True  # type:ignore[attr-defined]

    def record_discount(
        self,
        discount: dict[str, Decimal],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Extends parent class to record discount on the parent Voucher
        Ensures that parent save does not save it's children which would cause
        excessive writes."""
        if self.parent:
            self.parent.total_discount += discount["discount"]
            self.parent.save(update_children=False)
        return super().record_discount(discount, *args, **kwargs)

    record_discount.alters_data = True  # type:ignore[attr-defined]

    def _create_child(self, code: str, update_children: bool = True) -> Voucher | None:
        self._create_child_batch([code], update_children=update_children)
        obj = self.children.filter(code=code).first()
        return obj

    def _create_child_batch(
        self,
        codes: Sequence[str],
        batch_size: int = 1_000,
        update_children: bool = True,
    ) -> set[str]:
        children = []
        copy_fields = (
            "usage",
            "start_datetime",
            "end_datetime",
            "limit_usage_by_group",
        )
        for code in codes:
            child = self.__class__()
            child.parent = self
            child.code = code
            for field in copy_fields:
                setattr(child, field, getattr(self, field))
            children.append(child)
        # Bulk insert all the new codes
        objs = self.__class__.objects.bulk_create(
            children,
            ignore_conflicts=True,
            batch_size=batch_size,
        )
        # Bulk copy over the rest of the parent data
        if update_children:
            self.update_children()
        # Return the newly created codes as a set
        return {obj.code for obj in objs}

    def _get_child_code_batch(self, num_codes: int) -> list[str]:
        # The empty .order_by() clause is important here to prevent introducing
        # a bunch of JOINs for ordering by priority.
        existing_codes = set(
            self.__class__.objects.filter(code__startswith=self.code)
            .order_by()
            .values_list("code", flat=True)
            .iterator()
        )

        def check_code_is_unique(code: str) -> bool:
            return code not in existing_codes

        new_codes = []
        for i in range(num_codes):
            new_codes.append(
                self._get_child_code(
                    code_index=i,
                    max_index=num_codes,
                    check_code_is_unique=check_code_is_unique,
                )
            )
        return new_codes

    def _get_child_code(
        self,
        code_index: int,
        max_index: int,
        max_tries: int = 50,
        check_code_is_unique: Callable | None = None,
    ) -> str:
        if check_code_is_unique is None:

            def check_code_is_unique(code: str) -> bool:
                try:
                    self.__class__.objects.get(code=code)
                    return False
                except Voucher.DoesNotExist:
                    return True

        try_count = 0
        while try_count < max_tries:
            try_count += 1
            code = "{}-{}".format(
                self.code,
                self._get_code_uniquifier(code_index, max_index),
            )
            if check_code_is_unique(code=code):
                return code
        raise RuntimeError(
            _("Couldn't find a unique child code after %s iterations.") % try_count
        )

    def _get_code_uniquifier(
        self, code_index: int, max_index: int, extra_length: int = 3
    ) -> str:
        # Make sure all codes are the same length
        index = str(code_index).zfill(len(str(max_index)))
        # Append some digits to the end to make the codes non-sequential
        suffix = str(time.time()).replace(".", "")[-extra_length:]
        return f"{index}{suffix}"


from oscar.apps.voucher.models import *  # type:ignore[assignment]  # NOQA

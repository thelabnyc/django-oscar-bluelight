from django.db import models, transaction, connection
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from oscar.models.fields import NullCharField
from oscar.apps.voucher.abstract_models import AbstractVoucher
from . import tasks, sql
import time


class VoucherQuerySet(models.QuerySet):
    def exclude_children(self):
        return self.filter(parent=None)

    def select_for_update(self):
        """
        To do a select_for_updarte, we have to reset the query ordering so that it doesn't try to do
        outer joins to the ConditionalOffer and OfferGroup tables.
        """
        qs = self.order_by("pk")
        return models.QuerySet.select_for_update(qs)


class VoucherManager(models.Manager):
    def get_queryset(self):
        return VoucherQuerySet(self.model, using=self._db)

    def exclude_children(self):
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
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)

        # Child codes always get the parent's name
        def _get_parent_name():
            return instance.parent.name if instance.parent else None

        if instance.parent_id:
            parent_name = cache.get_or_set(
                instance._get_parent_name_cache_key(), _get_parent_name, 60
            )
            instance.name = parent_name
        return instance

    def _get_parent_name_cache_key(self, parent_id=None):
        if parent_id is None:
            parent_id = self.parent_id
        return f"oscarbluelight.Voucher.parent_name.{parent_id}"

    def is_active(self, test_datetime=None):
        ret = super().is_active(test_datetime)
        if self.is_suspended:
            return False
        return ret

    @property
    def offer_group(self):
        offer = self.offers.first()
        return offer.offer_group if offer else None

    @property
    def priority(self):
        offer = self.offers.first()
        return offer.priority if offer else 0

    @property
    def condition(self):
        offer = self.offers.first()
        return offer.condition if offer else None

    @property
    def benefit(self):
        offer = self.offers.first()
        return offer.benefit if offer else None

    @property
    def is_open(self):
        return self.status == self.OPEN

    @property
    def is_suspended(self):
        return self.status == self.SUSPENDED

    def suspend(self):
        self.status = self.SUSPENDED
        self.save()

    suspend.alters_data = True

    def unsuspend(self):
        self.status = self.OPEN
        self.save()

    unsuspend.alters_data = True

    def is_available_to_user(self, user=None):
        # Parent vouchers can not be used directly
        if self.list_children().exists():
            message = _("This voucher is not available")
            return False, message

        # Check whether the voucher is suspended or not
        if self.is_suspended:
            message = _("This voucher is currently inactive")
            return False, message

        # Enforce user group whitelisting
        if self.limit_usage_by_group:
            message = _("This voucher is only available to selected users")
            if not user:
                return False, message
            group_ids = set(g.id for g in self.groups.all())
            member_ids = set(g.id for g in user.groups.all())
            is_member = len(group_ids & member_ids) > 0
            if not is_member:
                return False, message

        # ignore statuses in BLUELIGHT_IGNORED_ORDER_STATUSES
        is_available, message = False, ""
        if self.usage == self.SINGLE_USE:
            is_available = not self.applications.exists()
            if not is_available:
                message = _("This voucher has already been used")
        elif self.usage == self.MULTI_USE:
            is_available = True
        elif self.usage == self.ONCE_PER_CUSTOMER:
            if not user.is_authenticated:
                is_available = False
                message = _("This voucher is only available to signed in users")
            else:
                is_available = (
                    not self.applications.exclude(
                        order__status__in=settings.BLUELIGHT_IGNORED_ORDER_STATUSES
                    )
                    .filter(voucher=self, user=user)
                    .exists()
                )
                if not is_available:
                    message = _(
                        "You have already used this voucher in " "a previous order"
                    )
        return is_available, message

    def list_children(self):
        return self.children.select_related("parent").all()

    @transaction.atomic
    def create_children(self, auto_generate_count=0, custom_codes=[]):
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
        success_count += len(self._create_child_batch(auto_gen_codes))
        # Save manual/custom codes
        custom_code_successes = self._create_child_batch(custom_codes)
        success_count += len(custom_code_successes)
        custom_code_failures = set(custom_codes) - custom_code_successes
        for code in sorted(list(custom_code_failures)):
            errors.append(
                _("Could not create code “%s” because it already exists.") % code
            )
        return errors, success_count

    @transaction.atomic
    def update_children(self):
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

    def save(self, update_children=True, *args, **kwargs):
        # Child codes use the parent's name and always store Null for their own name
        _orig_name = self.name
        if self.parent:
            self.name = None
            cache.delete(self._get_parent_name_cache_key(self.parent_id))
        else:
            cache.delete(self._get_parent_name_cache_key(self.pk))
        # Save the object
        rc = super().save(*args, **kwargs)
        # Update children?
        if update_children:
            tasks.update_child_vouchers.apply_async(args=(self.id,), countdown=10)
        # Restore the original name
        if self.parent:
            self.name = _orig_name
        return rc

    @transaction.atomic
    def delete(self, *args, **kwargs):
        offers = self.offers.all()
        rc = super().delete(*args, **kwargs)
        for offer in offers:
            # Delete the benefit and offer, since they're auto created
            condition = offer.condition
            offer.delete()
            if condition.offers.count() == 0:
                condition.delete()
        return rc

    def record_usage(self, order, user, *args, **kwargs):
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

    record_usage.alters_data = True

    def record_discount(self, discount, *args, **kwargs):
        """Extends parent class to record discount on the parent Voucher
        Ensures that parent save does not save it's children which would cause
        excessive writes."""
        if self.parent:
            self.parent.total_discount += discount["discount"]
            self.parent.save(update_children=False)
        return super().record_discount(discount, *args, **kwargs)

    record_discount.alters_data = True

    def _create_child(self, code):
        self._create_child_batch([code])
        obj = self.children.filter(code=code).first()
        return obj

    def _create_child_batch(self, codes, batch_size=10_000):
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
        self.update_children()
        # Return the newly created codes as a set
        return {obj.code for obj in objs}

    def _get_child_code_batch(self, num_codes):
        existing_codes = set(
            self.__class__.objects.all().values_list("code", flat=True)
        )

        def check_code_is_unique(code):
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
        self, code_index, max_index, max_tries=50, check_code_is_unique=None
    ):
        if check_code_is_unique is None:

            def check_code_is_unique(code):
                try:
                    self.__class__.objects.get(code=code)
                    return False
                except Voucher.DoesNotExist:
                    return True

        try_count = 0
        while try_count < max_tries:
            try_count += 1
            code = "%s-%s" % (
                self.code,
                self._get_code_uniquifier(code_index, max_index),
            )
            if check_code_is_unique(code=code):
                return code
        raise RuntimeError(
            _("Couldn't find a unique child code after %s iterations.") % try_count
        )

    def _get_code_uniquifier(self, code_index, max_index, extra_length=3):
        # Make sure all codes are the same length
        index = str(code_index).zfill(len(str(max_index)))
        # Append some digits to the end to make the codes non-sequential
        suffix = str(time.time()).replace(".", "")[-extra_length:]
        return "%s%s" % (index, suffix)


from oscar.apps.voucher.models import *  # noqa

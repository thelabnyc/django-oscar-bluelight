from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from oscar.models.fields import NullCharField
from oscar.apps.voucher.abstract_models import AbstractVoucher
from . import tasks
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

    objects = VoucherManager()

    class Meta:
        base_manager_name = "objects"
        ordering = ("-offers__offer_group__priority", "-offers__priority", "pk")

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # Child codes always get the parent's name
        if instance.parent:
            instance.name = instance.parent.name
        return instance

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

    def is_available_to_user(self, user=None):
        # Parent vouchers can not be used directly
        if self.children.exists():
            message = _("This voucher is not available")
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

        return super().is_available_to_user(user)

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
        for i in range(auto_generate_count):
            code = self._get_child_code(i, auto_generate_count)
            self._create_child(code)
            success_count += 1
        # Save manual/custom codes
        for code in custom_codes:
            if not Voucher.objects.filter(code__iexact=code).exists():
                self._create_child(code)
                success_count += 1
            else:
                errors.append(
                    _("Could not create code “%s” because it already exists.") % code
                )
        return errors, success_count

    @transaction.atomic
    def update_children(self):
        for child in self.children.all():
            self._update_child(child)

    @transaction.atomic
    def save(self, update_children=True, *args, **kwargs):
        # Child codes use the parent's name and always store Null for their own name
        _orig_name = self.name
        if self.parent:
            self.name = None
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
        child = self.__class__()
        child.code = code
        self._update_child(child)
        return child

    def _update_child(self, child):
        child.parent = self
        child.name = None
        copy_fields = (
            "usage",
            "start_datetime",
            "end_datetime",
            "limit_usage_by_group",
        )
        for field in copy_fields:
            setattr(child, field, getattr(self, field))
        # TODO: Might be useful to use django-dirtyfields here to prevent unnecessary DB writes.
        child.save(update_children=False)
        child.offers.set(list(self.offers.all()))
        child.groups.set(list(self.groups.all()))
        child.save(update_children=False)

    def _get_child_code(self, code_index, max_index, max_tries=50):
        try_count = 0
        while try_count < max_tries:
            try_count += 1
            code = "%s-%s" % (
                self.code,
                self._get_code_uniquifier(code_index, max_index),
            )
            try:
                self.__class__.objects.get(code=code)
            except Voucher.DoesNotExist:
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

from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from oscar.apps.voucher.abstract_models import AbstractVoucher
import time


class VoucherQuerySet(models.QuerySet):
    def exclude_children(self):
        return self.filter(parent=None)


class VoucherManager(models.Manager):
    def get_queryset(self):
        return VoucherQuerySet(self.model, using=self._db)

    def exclude_children(self):
        return self.get_queryset().exclude_children()


class Voucher(AbstractVoucher):
    parent = models.ForeignKey('self',
        verbose_name=_("Parent Voucher"),
        related_name='children',
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    limit_usage_by_group = models.BooleanField(_("Limit usage to selected user groups"), default=False)
    groups = models.ManyToManyField('auth.Group', verbose_name=_("User Groups"), blank=True)

    objects = VoucherManager()


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


    @transaction.atomic()
    def create_children(self, count):
        if self.parent is not None:
            raise RuntimeError('Can not create children for a child voucher. Nesting should only be 1 level.')
        if not self.id:
            self.save()
        children = []
        for i in range(count):
            code = self._get_child_code(i, count)
            child = self._create_child(i, code)
            children.append(child)
        return children

    @transaction.atomic()
    def save(self, *args, **kwargs):
        rc = super().save(*args, **kwargs)
        # TODO: This should probably be asynchronous, via Celery or something, to prevent
        # hanging for too long if there are a lot of codes.
        for child in self.children.all():
            self._update_child(child)
        return rc


    def record_usage(self, *args, **kwargs):
        if self.parent:
            self.parent.record_usage(*args, **kwargs)
        return super().record_usage(*args, **kwargs)
    record_usage.alters_data = True


    def record_discount(self, *args, **kwargs):
        if self.parent:
            self.parent.record_discount(*args, **kwargs)
        return super().record_discount(*args, **kwargs)
    record_discount.alters_data = True


    def _create_child(self, index, code):
        child = self.__class__()
        child.code = code
        self._update_child(child)
        return child


    def _update_child(self, child):
        child.parent = self
        copy_fields = ('name', 'usage', 'start_datetime', 'end_datetime', 'limit_usage_by_group')
        for field in copy_fields:
            setattr(child, field, getattr(self, field))
        # TODO: Might be useful to use django-dirtyfields here to prevent unnecessary DB writes.
        child.save()
        child.offers = list( self.offers.all() )
        child.groups = list( self.groups.all() )
        child.save()


    def _get_child_code(self, code_index, max_index, max_tries=50):
        try_count = 0
        while try_count < max_tries:
            try_count += 1
            code = "%s-%s" % (self.code, self._get_code_uniquifier(code_index, max_index))
            try:
                self.__class__.objects.get(code=code)
            except Voucher.DoesNotExist:
                return code
        raise RuntimeError("Couldn't find a unique child code after %s iterations." % try_count)


    def _get_code_uniquifier(self, code_index, max_index, extra_length=3):
        # Make sure all codes are the same length
        index = str(code_index).zfill(len(str(max_index)))
        # Append some digits to the end to make the codes non-sequential
        suffix = str(time.time()).replace('.', '')[-extra_length:]
        return "%s%s" % (index, suffix)


from oscar.apps.voucher.models import *  # noqa

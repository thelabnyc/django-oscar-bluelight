from decimal import Decimal as D, ROUND_UP
from django.core import exceptions
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import six
from oscar.apps.offer import utils
from oscar.apps.offer.conditions import CountCondition, CoverageCondition, ValueCondition
from oscar.core.loading import get_model
from oscar.templatetags.currency_filters import currency

Condition = get_model('offer', 'Condition')


def _default_clean(self):
    if not self.range:
        raise exceptions.ValidationError(_("Selected condition type requires a range."))
    if not self.value:
        raise exceptions.ValidationError(_("Selected condition type required a value."))


class BluelightCountCondition(CountCondition):
    _description = _("Basket includes %(count)d item(s) from %(range)s")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Count condition")
        verbose_name_plural = _("Count conditions")

    @property
    def name(self):
        return self._description % {
            'count': self.value,
            'range': six.text_type(self.range).lower() if self.range else 'product range'}

    @property
    def description(self):
        return self._description % {
            'count': self.value,
            'range': utils.range_anchor(self.range) if self.range else 'product range'}

    def _clean(self):
        return _default_clean(self)

    def consume_items(self, offer, basket, affected_lines):
        """
        Same as CountCondition.consume_items, except that it returns a list of consumed items. This
        is needed for CompoundCondition to be able to correctly consume items.
        """
        num_consumed = 0
        affected_lines = list(affected_lines)
        for line, __, quantity in affected_lines:
            num_consumed += quantity
        to_consume = max(0, self.value - num_consumed)
        if to_consume == 0:
            return affected_lines

        for __, line in self.get_applicable_lines(offer, basket, most_expensive_first=True):
            quantity_to_consume = min(line.quantity_without_discount, to_consume)
            line.consume(quantity_to_consume)
            affected_lines.append((line, 0, quantity_to_consume))
            to_consume -= quantity_to_consume
            if to_consume == 0:
                break
        return affected_lines


class BluelightCoverageCondition(CoverageCondition):
    _description = _("Basket includes %(count)d distinct item(s) from %(range)s")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Coverage Condition")
        verbose_name_plural = _("Coverage Conditions")

    @property
    def name(self):
        return self._description % {
            'count': self.value,
            'range': six.text_type(self.range).lower() if self.range else 'product range'}

    @property
    def description(self):
        return self._description % {
            'count': self.value,
            'range': utils.range_anchor(self.range) if self.range else 'product range'}

    def _clean(self):
        return _default_clean(self)

    def consume_items(self, offer, basket, affected_lines):
        """
        Same as CoverageCondition.consume_items, except that it returns a list of consumed items. This
        is needed for CompoundCondition to be able to correctly consume items.
        """
        consumed_products = []
        affected_lines = list(affected_lines)
        for line, __, quantity in affected_lines:
            consumed_products.append(line.product)

        to_consume = max(0, self.value - len(consumed_products))
        if to_consume == 0:
            return affected_lines

        for line in basket.all_lines():
            product = line.product
            if not self.can_apply_condition(line):
                continue
            if product in consumed_products:
                continue
            if not line.is_available_for_discount:
                continue
            # Only consume a quantity of 1 from each line
            line.consume(1)
            affected_lines.append((line, 0, 1))
            consumed_products.append(product)
            to_consume -= 1
            if to_consume == 0:
                break
        return affected_lines


class BluelightValueCondition(ValueCondition):
    _description = _("Basket includes %(amount)s from %(range)s")

    class Meta:
        app_label = 'offer'
        proxy = True
        verbose_name = _("Value condition")
        verbose_name_plural = _("Value conditions")

    @property
    def name(self):
        return self._description % {
            'amount': currency(self.value),
            'range': six.text_type(self.range).lower() if self.range else 'product range'}

    @property
    def description(self):
        return self._description % {
            'amount': currency(self.value),
            'range': utils.range_anchor(self.range) if self.range else 'product range'}

    def _clean(self):
        return _default_clean(self)

    def consume_items(self, offer, basket, affected_lines):
        """
        Same as ValueCondition.consume_items, except that it returns a list of consumed items. This
        is needed for CompoundCondition to be able to correctly consume items.
        """
        value_consumed = D('0.00')
        affected_lines = list(affected_lines)
        for line, __, qty in affected_lines:
            price = utils.unit_price(offer, line)
            value_consumed += price * qty

        to_consume = max(0, self.value - value_consumed)
        if to_consume == 0:
            return affected_lines

        for price, line in self.get_applicable_lines(offer, basket, most_expensive_first=True):
            quantity_to_consume = (to_consume / price).quantize(D(1), ROUND_UP)
            quantity_to_consume = min(line.quantity_without_discount, quantity_to_consume)
            line.consume(quantity_to_consume)
            affected_lines.append((line, 0, quantity_to_consume))
            to_consume -= price * quantity_to_consume
            if to_consume <= 0:
                break
        return affected_lines


class CompoundCondition(Condition):
    """
    An offer condition that aggregates together multiple other conditions,
    allowing the creation of compound rules for offers.
    """
    AND, OR = ("AND", "OR")
    CONJUNCTION_TYPE_CHOICES = (
        (AND, _("Logical AND")),
        (OR, _("Logical OR")),
    )
    conjunction = models.CharField(
        _("Subcondition conjunction type"), choices=CONJUNCTION_TYPE_CHOICES,
        default=AND, max_length=10)

    subconditions = models.ManyToManyField('offer.Condition', related_name='parent_conditions')

    class Meta:
        app_label = 'offer'
        verbose_name = _("Compound condition")
        verbose_name_plural = _("Compound conditions")

    @property
    def children(self):
        if self.pk is None:
            return []
        chil = [c for c in self.subconditions.order_by('id').all() if c.id != self.id]
        return chil

    @property
    def name(self):
        names = (c.name for c in self.children)
        return self._human_readable_conjoin(names, 'Empty Condition')

    @property
    def description(self):
        descrs = (c.description for c in self.children)
        return self._human_readable_conjoin(descrs, 'Empty Condition')

    def _clean(self):
        if self.range:
            raise exceptions.ValidationError(_("Compound conditions should not have a range."))
        if self.value:
            raise exceptions.ValidationError(_("Compound conditions should not have a value."))

    def is_satisfied(self, *args):
        return self._reduce_results(self.conjunction, 'is_satisfied', *args)

    def is_partially_satisfied(self, *args):
        return self._reduce_results(self.OR, 'is_partially_satisfied', *args)

    def get_upsell_message(self, offer, basket):
        messages = []
        for c in self.children:
            condition = c.proxy()
            partial = condition.is_partially_satisfied(offer, basket)
            complete = condition.is_satisfied(offer, basket)
            if not complete and partial:
                messages.append(condition.get_upsell_message(offer, basket))
        return self._human_readable_conjoin(messages)

    def consume_items(self, offer, basket, affected_lines):
        memo = affected_lines
        for c in self.children:
            affected_lines = c.proxy().consume_items(offer, basket, memo)
            if affected_lines and affected_lines.__iter__:
                memo = affected_lines
        return affected_lines

    def _human_readable_conjoin(self, strings, empty=None):
        labels = {
            self.AND: _(' and '),
            self.OR: _(' or '),
        }
        strings = list(strings)
        if len(strings) <= 0 and empty is not None:
            return empty
        return labels[self.conjunction].join(strings)

    def _reduce_results(self, conjunction, method_name, *args):
        result = self._get_conjunction_root_memo(conjunction)
        for c in self.children:
            condition = c.proxy()
            fn = getattr(condition, method_name)
            subresult = fn(*args)
            result = self._apply_conjunction(conjunction, result, subresult)
        return result

    def _get_conjunction_root_memo(self, conjunction):
        memos = {
            self.AND: True,
            self.OR: False,
        }
        return memos[conjunction]

    def _apply_conjunction(self, conjunction, a, b):
        fns = {
            self.AND: lambda: a and b,
            self.OR: lambda: a or b,
        }
        return fns[conjunction]()


__all__ = [
    'BluelightCountCondition',
    'BluelightCoverageCondition',
    'BluelightValueCondition',
    'CompoundCondition',
]

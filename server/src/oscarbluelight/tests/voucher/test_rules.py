from datetime import datetime
from django.contrib.auth.models import AnonymousUser, User, Group
from django.test import TestCase
from django.utils import timezone
from oscarbluelight.voucher.models import Voucher
from oscarbluelight.voucher.rules import (
    VoucherHasChildrenRule,
    VoucherSuspendedRule,
    VoucherLimitUsageByGroupRule,
    VoucherSingleUseRule,
    VoucherSingleUsePerCustomerRule,
)
from oscar.test.factories import create_order


class VoucherHasChildrenRuleTest(TestCase):
    def test_is_obeyed_by_user(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )
        applied_rule = VoucherHasChildrenRule(p, user)
        self.assertFalse(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "This voucher is not available")

        applied_rule = VoucherHasChildrenRule(c, user)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")


class VoucherSuspendedRuleTest(TestCase):
    def test_is_obeyed_by_user(self):
        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timezone.timedelta(days=1),
            limit_usage_by_group=False,
        )
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )

        voucher.suspend()
        self.assertTrue(voucher.is_suspended)
        applied_rule = VoucherSuspendedRule(voucher, user)
        self.assertFalse(applied_rule.is_obeyed_by_user())
        self.assertEqual(
            applied_rule.get_msg_text(), "This voucher is currently inactive"
        )

        voucher.unsuspend()
        self.assertTrue(voucher.is_open)
        applied_rule = VoucherSuspendedRule(voucher, user)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")


class VoucherLimitUsageByGroupRuleTest(TestCase):
    def test_is_obeyed_by_anonymous_user(self):
        user = AnonymousUser()
        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        applied_rule = VoucherLimitUsageByGroupRule(voucher, user)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")

        voucher.limit_usage_by_group = True
        voucher.save()

        applied_rule = VoucherLimitUsageByGroupRule(voucher, user)
        self.assertFalse(applied_rule.is_obeyed_by_user())
        self.assertEqual(
            applied_rule.get_msg_text(),
            "This voucher is only available to selected users",
        )

    def test_is_obeyed_by_authenticated_user(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )

        customer = Group.objects.create(name="Customers")

        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        applied_rule = VoucherLimitUsageByGroupRule(voucher, user)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")

        voucher.groups.set([customer])
        voucher.save()

        applied_rule = VoucherLimitUsageByGroupRule(voucher, user)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")

        voucher.limit_usage_by_group = True
        voucher.save()

        applied_rule = VoucherLimitUsageByGroupRule(voucher, user)
        self.assertFalse(applied_rule.is_obeyed_by_user())
        self.assertEqual(
            applied_rule.get_msg_text(),
            "This voucher is only available to selected users",
        )

        user.groups.set([customer])
        user.save()

        applied_rule = VoucherLimitUsageByGroupRule(voucher, user)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")


class VoucherSingleUseRuleTest(TestCase):
    def test_is_obeyed_by_user(self):
        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timezone.timedelta(days=1),
            limit_usage_by_group=False,
        )
        user1 = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )
        user2 = User.objects.create_user(
            username="john", email="john@example.com", password="foo"
        )
        order1 = create_order()

        applied_rule = VoucherSingleUseRule(voucher, user1)
        self.assertEqual(voucher.applications.all().count(), 0)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")

        voucher.record_usage(order1, user1)
        self.assertEqual(voucher.applications.all().count(), 1)

        applied_rule = VoucherSingleUseRule(voucher, user2)
        self.assertFalse(applied_rule.is_obeyed_by_user())
        self.assertEqual(
            applied_rule.get_msg_text(), "This coupon has already been used"
        )


class VoucherSingleUsePerCustomerRuleTest(TestCase):
    def test_is_obeyed_by_user(self):
        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.ONCE_PER_CUSTOMER,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timezone.timedelta(days=1),
            limit_usage_by_group=False,
        )
        user1 = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )
        user2 = User.objects.create_user(
            username="john", email="john@example.com", password="foo"
        )
        order1 = create_order()
        order2 = create_order()

        applied_rule = VoucherSingleUsePerCustomerRule(voucher, user1)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")

        voucher.record_usage(order1, user1)

        applied_rule = VoucherSingleUsePerCustomerRule(voucher, user2)
        self.assertTrue(applied_rule.is_obeyed_by_user())
        self.assertEqual(applied_rule.get_msg_text(), "")

        voucher.record_usage(order2, user2)

        applied_rule = VoucherSingleUsePerCustomerRule(voucher, user1)
        self.assertFalse(applied_rule.is_obeyed_by_user())
        self.assertEqual(
            applied_rule.get_msg_text(),
            "You have already used this coupon in a previous order",
        )

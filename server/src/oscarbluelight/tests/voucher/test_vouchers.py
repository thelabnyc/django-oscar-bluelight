from datetime import datetime
from decimal import Decimal as D
from django.test import TestCase, override_settings
from django.utils import timezone
from oscarbluelight.voucher.models import Voucher
from django.contrib.auth.models import AnonymousUser, User, Group
from oscar.test.factories import create_order


class UserGroupWhitelistTest(TestCase):
    def test_anonymous_user(self):
        user = AnonymousUser()
        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

        voucher.limit_usage_by_group = True
        voucher.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is only available to selected users")

    def test_authenticated_user(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )

        customer = Group.objects.create(name="Customers")
        csrs = Group.objects.create(name="Customer Service Reps")

        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

        voucher.groups.set([csrs])
        voucher.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

        voucher.limit_usage_by_group = True
        voucher.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is only available to selected users")

        user.groups.set([customer])
        user.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is only available to selected users")

        user.groups.set([csrs])
        user.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)


class ParentChildVoucherTest(TestCase):
    def test_exclude_children_clause(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        self.assertEqual(Voucher.objects.all().count(), 3)
        self.assertEqual(Voucher.objects.exclude_children().all().count(), 1)
        self.assertEqual(Voucher.objects.order_by("code").all().count(), 3)
        self.assertEqual(
            Voucher.objects.order_by("code").exclude_children().all().count(), 1
        )
        self.assertEqual(Voucher.objects.exclude_children().get().code, "TEST-VOUCHER")

    def test_parent_voucher_is_not_available(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )

        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        self.assertTrue(p.is_available_to_user(user)[0])

        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        self.assertFalse(p.is_available_to_user(user)[0])
        self.assertTrue(c1.is_available_to_user(user)[0])

    def test_create_children(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        self.assertEqual(p.children.all().count(), 0)

        p.create_children(auto_generate_count=10)
        self.assertEqual(p.children.all().count(), 10)

        c1 = p.children.order_by("code").first()
        self.assertEqual(c1.name, "Test Voucher")
        self.assertTrue(c1.code.startswith("TEST-VOUCHER-00"))
        self.assertEqual(c1.usage, Voucher.SINGLE_USE)
        self.assertEqual(c1.start_datetime, p.start_datetime)
        self.assertEqual(c1.end_datetime, p.end_datetime)
        self.assertFalse(c1.limit_usage_by_group)

    def test_create_lots_of_children(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        self.assertEqual(p.children.all().count(), 0)

        # First batch. Query count should be (17 + (auto_generate_count / 10_000)), since
        # the `bulk_create` batch size is 10_000
        baseline_num_queries = 17
        insert_batch_size = 10_000
        auto_generate_count = 100_000
        with self.assertNumQueries(
            baseline_num_queries + (auto_generate_count / insert_batch_size)
        ):
            p.create_children(auto_generate_count=auto_generate_count)

        self.assertEqual(p.children.all().count(), 100_000)

        # Second batch. This tests the performance of checking new codes for
        # conflicts against existing codes.
        auto_generate_count = 200_000
        with self.assertNumQueries(
            baseline_num_queries + (auto_generate_count / insert_batch_size)
        ):
            p.create_children(auto_generate_count=auto_generate_count)

        self.assertEqual(p.children.all().count(), 300_000)

    def test_update_parent(self):
        customer = Group.objects.create(name="Customers")
        csrs = Group.objects.create(name="Customer Service Reps")

        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        p.groups.set([customer])
        self.assertEqual(p.children.all().count(), 0)

        p.create_children(auto_generate_count=1)
        self.assertEqual(p.children.all().count(), 1)

        c1 = p.children.order_by("code").first()
        self.assertEqual(c1.name, "Test Voucher")
        self.assertTrue(c1.code.startswith("TEST-VOUCHER-0"))
        self.assertEqual(c1.usage, Voucher.SINGLE_USE)
        self.assertEqual(c1.start_datetime, p.start_datetime)
        self.assertEqual(c1.end_datetime, p.end_datetime)
        self.assertFalse(c1.limit_usage_by_group)
        self.assertEqual(c1.groups.count(), 1)
        self.assertEqual(c1.groups.get(), customer)

        p.name = "Some Other Name"
        p.groups.set([csrs])
        p.save()

        c1 = p.children.order_by("code").first()
        self.assertEqual(c1.name, "Some Other Name")
        self.assertTrue(c1.code.startswith("TEST-VOUCHER-0"))
        self.assertEqual(c1.usage, Voucher.SINGLE_USE)
        self.assertEqual(c1.start_datetime, p.start_datetime)
        self.assertEqual(c1.end_datetime, p.end_datetime)
        self.assertFalse(c1.limit_usage_by_group)
        self.assertEqual(c1.groups.count(), 1)
        self.assertEqual(c1.groups.get(), csrs)

    def test_delete_parent(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c2 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        self.assertEqual(Voucher.objects.all().count(), 3)
        c2.delete()
        self.assertEqual(Voucher.objects.all().count(), 2)
        p.delete()
        self.assertEqual(Voucher.objects.all().count(), 0)

    def test_record_usage(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )
        order = create_order()

        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c2 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        self.assertEqual(p.num_orders, 0)
        self.assertEqual(c1.num_orders, 0)
        self.assertEqual(c2.num_orders, 0)
        self.assertEqual(p.applications.all().count(), 0)
        self.assertEqual(c1.applications.all().count(), 0)
        self.assertEqual(c2.applications.all().count(), 0)

        c1.record_usage(order, user)

        self.assertEqual(p.num_orders, 1)
        self.assertEqual(c1.num_orders, 1)
        self.assertEqual(c2.num_orders, 0)
        self.assertEqual(p.applications.all().count(), 1)
        self.assertEqual(c1.applications.all().count(), 1)
        self.assertEqual(c2.applications.all().count(), 0)

        self.assertEqual(p.applications.first().order, order)
        self.assertEqual(c1.applications.first().order, order)
        self.assertEqual(p.applications.first().user, user)
        self.assertEqual(c1.applications.first().user, user)

    def test_no_excessive_saving(self):
        """Ensure that record usage does not trigger excessive db writes on
        all siblings"""
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-x",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        # These vouchers shouldn't save
        for i in range(5):
            Voucher.objects.create(
                parent=p,
                name="Test Voucher",
                code="test-voucher-{}".format(i),
                usage=Voucher.MULTI_USE,
                start_datetime=datetime.now(),
                end_datetime=datetime.now(),
                limit_usage_by_group=False,
            )

        with self.assertNumQueries(11):
            c1.record_discount({"discount": 5})

    def test_record_discount(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c2 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )

        self.assertEqual(p.total_discount, D("0.00"))
        self.assertEqual(c1.total_discount, D("0.00"))
        self.assertEqual(c2.total_discount, D("0.00"))

        c1.record_discount({"discount": D("7.00")})

        self.assertEqual(p.total_discount, D("7.00"))
        self.assertEqual(c1.total_discount, D("7.00"))
        self.assertEqual(c2.total_discount, D("0.00"))

        c2.record_discount({"discount": D("3.00")})

        self.assertEqual(p.total_discount, D("10.00"))
        self.assertEqual(c1.total_discount, D("7.00"))
        self.assertEqual(c2.total_discount, D("3.00"))


class VoucherNotUsedForIgnoredStatus(TestCase):
    @override_settings(BLUELIGHT_IGNORED_ORDER_STATUSES=["Pending"])
    def test_voucher_available_if_used_on_ignored_order_status(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )
        ignore_order = create_order()
        ignore_order.status = "Pending"
        ignore_order.save()
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False,
        )
        c1.record_usage(ignore_order, user)
        self.assertTrue(c1.is_available_to_user(user))
        # not available after used on order with non ignored status
        order = create_order()
        ignore_order.status = "Authorized"
        ignore_order.save()
        c1.record_usage(order, user)
        is_available, message = c1.is_available_to_user(user)
        self.assertFalse(is_available)


class VoucherSuspensionTest(TestCase):
    def test_suspend_voucher(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )

        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timezone.timedelta(days=1),
            limit_usage_by_group=False,
        )

        self.assertTrue(voucher.is_active())
        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

        voucher.suspend()
        self.assertTrue(voucher.is_suspended)
        self.assertFalse(voucher.is_active())
        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is currently inactive")

    def test_unsuspend_voucher(self):
        user = User.objects.create_user(
            username="bob", email="bob@example.com", password="foo"
        )

        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timezone.timedelta(days=1),
            limit_usage_by_group=False,
            status=Voucher.SUSPENDED,
        )

        self.assertFalse(voucher.is_active())
        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is currently inactive")

        voucher.unsuspend()
        self.assertTrue(voucher.is_open)
        self.assertTrue(voucher.is_active())
        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

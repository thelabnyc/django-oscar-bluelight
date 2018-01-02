from datetime import datetime
from decimal import Decimal as D
from django.test import TestCase
from oscarbluelight.voucher.models import Voucher
from django.contrib.auth.models import AnonymousUser, User, Group
from oscar.test.factories import create_order


class UserGroupWhitelistTest(TestCase):
    def test_anonymous_user(self):
        user = AnonymousUser()
        voucher = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

        voucher.limit_usage_by_group = True
        voucher.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is only available to selected users")


    def test_authenticated_user(self):
        user = User.objects.create_user(
            username='bob', email='bob@example.com', password='foo')

        customer = Group.objects.create(name='Customers')
        csrs = Group.objects.create(name='Customer Service Reps')

        voucher = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

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
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-1',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-2',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        self.assertEqual(Voucher.objects.all().count(), 3)
        self.assertEqual(Voucher.objects.exclude_children().all().count(), 1)
        self.assertEqual(Voucher.objects.order_by('code').all().count(), 3)
        self.assertEqual(Voucher.objects.order_by('code').exclude_children().all().count(), 1)
        self.assertEqual(Voucher.objects.exclude_children().get().code, 'TEST-VOUCHER')


    def test_parent_voucher_is_not_available(self):
        user = User.objects.create_user(
            username='bob', email='bob@example.com', password='foo')

        p = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

        self.assertTrue( p.is_available_to_user(user)[0] )

        c1 = Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-1',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

        self.assertFalse( p.is_available_to_user(user)[0] )
        self.assertTrue( c1.is_available_to_user(user)[0] )



    def test_create_children(self):
        p = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        self.assertEqual(p.children.all().count(), 0)

        p.create_children(10)
        self.assertEqual(p.children.all().count(), 10)

        c1 = p.children.order_by('code').first()
        self.assertEqual(c1.name, 'Test Voucher')
        self.assertTrue( c1.code.startswith('TEST-VOUCHER-00') )
        self.assertEqual(c1.usage, Voucher.SINGLE_USE)
        self.assertEqual(c1.start_datetime, p.start_datetime)
        self.assertEqual(c1.end_datetime, p.end_datetime)
        self.assertFalse(c1.limit_usage_by_group)


    def test_update_parent(self):
        p = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        self.assertEqual(p.children.all().count(), 0)

        p.create_children(1)
        self.assertEqual(p.children.all().count(), 1)

        c1 = p.children.order_by('code').first()
        self.assertEqual(c1.name, 'Test Voucher')
        self.assertTrue( c1.code.startswith('TEST-VOUCHER-0') )
        self.assertEqual(c1.usage, Voucher.SINGLE_USE)
        self.assertEqual(c1.start_datetime, p.start_datetime)
        self.assertEqual(c1.end_datetime, p.end_datetime)
        self.assertFalse(c1.limit_usage_by_group)

        p.name = 'Some Other Name'
        p.save()

        c1 = p.children.order_by('code').first()
        self.assertEqual(c1.name, 'Some Other Name')
        self.assertTrue( c1.code.startswith('TEST-VOUCHER-0') )
        self.assertEqual(c1.usage, Voucher.SINGLE_USE)
        self.assertEqual(c1.start_datetime, p.start_datetime)
        self.assertEqual(c1.end_datetime, p.end_datetime)
        self.assertFalse(c1.limit_usage_by_group)


    def test_delete_parent(self):
        p = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-1',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        c2 = Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-2',
            usage=Voucher.SINGLE_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

        self.assertEqual(Voucher.objects.all().count(), 3)
        c2.delete()
        self.assertEqual(Voucher.objects.all().count(), 2)
        p.delete()
        self.assertEqual(Voucher.objects.all().count(), 0)


    def test_record_usage(self):
        user = User.objects.create_user(
            username='bob', email='bob@example.com', password='foo')
        order = create_order()

        p = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        c1 = Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-1',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        c2 = Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-2',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

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
        """ Ensure that record usage does not trigger excessive db writes on
        all siblings """
        p = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        c1 = Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-x',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

        # These vouchers shouldn't save
        for i in range(5):
            Voucher.objects.create(
                parent=p,
                name='Test Voucher',
                code='test-voucher-{}'.format(i),
                usage=Voucher.MULTI_USE,
                start_datetime=datetime.now(),
                end_datetime=datetime.now(),
                limit_usage_by_group=False)

        with self.assertNumQueries(10):
            c1.record_discount({"discount": 5})

    def test_record_discount(self):
        p = Voucher.objects.create(
            name='Test Voucher',
            code='test-voucher',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        c1 = Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-1',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)
        c2 = Voucher.objects.create(
            parent=p,
            name='Test Voucher',
            code='test-voucher-2',
            usage=Voucher.MULTI_USE,
            start_datetime=datetime.now(),
            end_datetime=datetime.now(),
            limit_usage_by_group=False)

        self.assertEqual(p.total_discount, D('0.00'))
        self.assertEqual(c1.total_discount, D('0.00'))
        self.assertEqual(c2.total_discount, D('0.00'))

        c1.record_discount({ 'discount': D('7.00') })

        self.assertEqual(p.total_discount, D('7.00'))
        self.assertEqual(c1.total_discount, D('7.00'))
        self.assertEqual(c2.total_discount, D('0.00'))

        c2.record_discount({ 'discount': D('3.00') })

        self.assertEqual(p.total_discount, D('10.00'))
        self.assertEqual(c1.total_discount, D('7.00'))
        self.assertEqual(c2.total_discount, D('3.00'))

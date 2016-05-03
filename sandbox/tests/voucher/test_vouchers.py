from datetime import datetime
from django.test import TestCase
from bluelight.voucher.models import Voucher
from django.contrib.auth.models import AnonymousUser, User, Group


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

        voucher.groups = [csrs]
        voucher.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

        voucher.limit_usage_by_group = True
        voucher.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is only available to selected users")

        user.groups = [customer]
        user.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertFalse(is_available)
        self.assertEqual(message, "This voucher is only available to selected users")

        user.groups = [csrs]
        user.save()

        is_available, message = voucher.is_available_to_user(user)
        self.assertTrue(is_available)

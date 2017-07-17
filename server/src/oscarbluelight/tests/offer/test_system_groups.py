from unittest import mock
from django.test import TestCase
from oscarbluelight.offer.applicator import Applicator
from oscarbluelight.offer.models import OfferGroup
from oscarbluelight.offer.signals import pre_offer_group_apply, post_offer_group_apply
from oscarbluelight.offer.groups import (
    register_system_offer_group,
    pre_offer_group_apply_receiver,
    post_offer_group_apply_receiver,
)


class OfferGroupModelTest(TestCase):
    def test_register_system_offer_group(self):
        # System group should not exist yet
        self.assertEqual(OfferGroup.objects.filter(slug='my-system-group').count(), 0)

        # Register a system group
        my_system_group = register_system_offer_group('my-system-group', default_name='My System Group')

        # System group should still not exist yet due to lazy-evaluation
        self.assertEqual(OfferGroup.objects.filter(slug='my-system-group').count(), 0)

        # Access some model properties, triggering lazy-evaluation
        self.assertEqual(my_system_group.name, 'My System Group')
        self.assertEqual(my_system_group.slug, 'my-system-group')
        self.assertEqual(my_system_group.priority, 1001)
        self.assertEqual(my_system_group.is_system_group, True)

        # System group should exist now
        self.assertEqual(OfferGroup.objects.filter(slug='my-system-group').count(), 1)


    def test_register_system_offer_group_with_existing_groups(self):
        # Make a couple pre-existing OfferGroups
        OfferGroup.objects.create(
            name='Low Priority Offers',
            priority=25)
        OfferGroup.objects.create(
            name='Medium Priority Offers',
            priority=500)
        OfferGroup.objects.create(
            name='High Priority Offers',
            priority=1500)

        # Register a system group
        my_system_group = register_system_offer_group('my-system-group', default_name='My System Group')

        # System group should have automatically gotten priority 1 higher than any pre-existing group
        self.assertEqual(my_system_group.name, 'My System Group')
        self.assertEqual(my_system_group.slug, 'my-system-group')
        self.assertEqual(my_system_group.priority, 1501)
        self.assertEqual(my_system_group.is_system_group, True)

        # System group should exist now
        self.assertEqual(OfferGroup.objects.filter(slug='my-system-group').count(), 1)

        # Registering the same system group again should change it's priority
        my_system_group = register_system_offer_group('my-system-group', default_name='My System Group')
        self.assertEqual(my_system_group.priority, 1501)
        self.assertEqual(OfferGroup.objects.filter(slug='my-system-group').count(), 1)


    def test_receivers(self):
        # Build some offer groups
        group1 = OfferGroup.objects.create(slug='group-1', name='Group 1', priority=1, is_system_group=True)
        group2 = OfferGroup.objects.create(slug='group-2', name='Group 2', priority=2, is_system_group=True)

        # Build some mock signal listeners
        handler1_pre = mock.MagicMock()
        handler1_post = mock.MagicMock()
        handler2_pre = mock.MagicMock()
        handler2_post = mock.MagicMock()

        # Connect the listeners to the signals
        pre_offer_group_apply_receiver('group-1')(handler1_pre)
        post_offer_group_apply_receiver('group-1')(handler1_post)
        pre_offer_group_apply_receiver('group-2')(handler2_pre)
        post_offer_group_apply_receiver('group-2')(handler2_post)

        # Make sure nothing has gotten called yet
        handler1_pre.assert_not_called()
        handler1_post.assert_not_called()
        handler2_pre.assert_not_called()
        handler2_post.assert_not_called()

        # Send group1 pre
        pre_offer_group_apply.send(sender=Applicator, basket=None, group=group1, offers=[])

        # Ensure correct handler was called
        handler1_pre.assert_called_once_with(Applicator, basket=None, group=group1, offers=[], signal=pre_offer_group_apply)
        handler1_post.assert_not_called()
        handler2_pre.assert_not_called()
        handler2_post.assert_not_called()

        # Send group1 post
        post_offer_group_apply.send(sender=Applicator, basket=None, group=group1, offers=[])

        # Ensure correct handler was called
        handler1_pre.assert_called_once_with(Applicator, basket=None, group=group1, offers=[], signal=pre_offer_group_apply)
        handler1_post.assert_called_once_with(Applicator, basket=None, group=group1, offers=[], signal=post_offer_group_apply)
        handler2_pre.assert_not_called()
        handler2_post.assert_not_called()

        # Send group2 pre
        pre_offer_group_apply.send(sender=Applicator, basket=None, group=group2, offers=[])

        # Ensure correct handler was called
        handler1_pre.assert_called_once_with(Applicator, basket=None, group=group1, offers=[], signal=pre_offer_group_apply)
        handler1_post.assert_called_once_with(Applicator, basket=None, group=group1, offers=[], signal=post_offer_group_apply)
        handler2_pre.assert_called_once_with(Applicator, basket=None, group=group2, offers=[], signal=pre_offer_group_apply)
        handler2_post.assert_not_called()

        # Send group2 post
        post_offer_group_apply.send(sender=Applicator, basket=None, group=group2, offers=[])

        # Ensure correct handler was called
        handler1_pre.assert_called_once_with(Applicator, basket=None, group=group1, offers=[], signal=pre_offer_group_apply)
        handler1_post.assert_called_once_with(Applicator, basket=None, group=group1, offers=[], signal=post_offer_group_apply)
        handler2_pre.assert_called_once_with(Applicator, basket=None, group=group2, offers=[], signal=pre_offer_group_apply)
        handler2_post.assert_called_once_with(Applicator, basket=None, group=group2, offers=[], signal=post_offer_group_apply)

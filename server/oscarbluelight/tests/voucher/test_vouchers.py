from decimal import Decimal as D
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from oscar.test.factories import create_order

from oscarbluelight.voucher.models import Voucher


class UserGroupWhitelistTest(TestCase):
    def test_anonymous_user(self):
        user = AnonymousUser()
        voucher = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )

        self.assertTrue(p.is_available_to_user(user)[0])

        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )

        self.assertFalse(p.is_available_to_user(user)[0])
        self.assertTrue(c1.is_available_to_user(user)[0])

    def test_create_children(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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

    def test_create_children_mixed_auto_and_custom(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        custom_codes = ["CUSTOM-A", "CUSTOM-B"]
        p.create_children(auto_generate_count=5, custom_codes=custom_codes)
        self.assertEqual(p.children.all().count(), 7)
        # Verify custom codes exist
        created_codes = set(p.children.values_list("code", flat=True))
        self.assertIn("CUSTOM-A", created_codes)
        self.assertIn("CUSTOM-B", created_codes)
        # Verify auto-generated codes exist
        auto_codes = [c for c in created_codes if c.startswith("TEST-VOUCHER-")]
        self.assertEqual(len(auto_codes), 5)

    def test_create_children_with_custom_codes(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        custom_codes = ["CUSTOM-1", "CUSTOM-2", "CUSTOM-3"]
        p.create_children(custom_codes=custom_codes)
        self.assertEqual(
            set(p.children.values_list("code", flat=True)),
            {"CUSTOM-1", "CUSTOM-2", "CUSTOM-3"},
        )

    def test_create_children_with_duplicate_custom_codes(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        # Create initial child with custom code
        p.create_children(custom_codes=["CUSTOM-1"])
        self.assertEqual(set(p.children.values_list("code", flat=True)), {"CUSTOM-1"})
        p.create_children(custom_codes=["CUSTOM-1", "CUSTOM-2"])
        # Verify there are 2 unique codes and duplicate was silently ignored because
        # bulk_create with ignore_conflicts=True only inserts the non-conflicting ones into the database
        self.assertEqual(
            set(p.children.values_list("code", flat=True)), {"CUSTOM-1", "CUSTOM-2"}
        )

    def test_create_lots_of_children(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        self.assertEqual(p.children.all().count(), 0)

        # First batch. Query count should be (3 + (auto_generate_count / 1_000) + ceil(auto_generate_count / 10_000)),
        # since the `bulk_create` batch size is 1,000 and the round `chunk_size` is 10,000.
        # Query breakdown:
        # - 3 baseline (transaction start/commit + existing children count)
        # - bulk_create batches (auto_generate_count / insert_batch_size), so for 100 thousand codes = 100 queries
        # - check for existing codes in _get_child_code_batch: 1 query per round,
        #   rounds = ceil(auto_generate_count / chunk_size), so for 100 thousand codes = 10 rounds
        # Total: 3 + 100 + 10 = 113 queries
        baseline_num_queries = 3
        round_chunk_size = 10_000
        insert_batch_size = 1_000
        auto_generate_count = 100_000
        # Mock _get_code_uniquifier to ensure deterministic suffixes.
        # This prevents random collisions while still testing the actual code path with queries
        call_count = [0]

        def mock_get_code_uniquifier(code_index, max_index, extra_length=3):
            # Return deterministic uniquifier instead of timestamp-based one
            call_count[0] += 1
            index = str(code_index).zfill(len(str(max_index)))
            suffix = str(call_count[0]).zfill(extra_length)
            return f"{index}{suffix}"

        with patch.object(
            p, "_get_code_uniquifier", side_effect=mock_get_code_uniquifier
        ):
            # Calculate expected queries with deterministic generation (no random conflicts)
            rounds = (auto_generate_count + round_chunk_size - 1) // round_chunk_size
            bulk_creates = auto_generate_count // insert_batch_size
            expected_queries = baseline_num_queries + rounds + bulk_creates
            with self.assertNumQueries(expected_queries):
                p.create_children(auto_generate_count=auto_generate_count)
            self.assertEqual(p.children.all().count(), 100_000)

        # Second batch. This tests the performance of checking new codes for
        # no conflicts against existing codes.
        # Query breakdown:
        # - 3 baseline (transaction start/commit + existing children count)
        # - bulk_create batches (auto_generate_count / insert_batch_size), so for 200 thousand codes = 200 queries
        # - check for existing codes in _get_child_code_batch: 1 query per round,
        #   rounds = ceil(auto_generate_count / chunk_size), so for 200 thousand codes = 20 rounds
        # Total: 3 + 200 + 20 = 223 queries
        auto_generate_count = 200_000
        with patch.object(
            p, "_get_code_uniquifier", side_effect=mock_get_code_uniquifier
        ):
            rounds = (auto_generate_count + round_chunk_size - 1) // round_chunk_size
            bulk_creates = auto_generate_count // insert_batch_size
            expected_queries = baseline_num_queries + rounds + bulk_creates
            with self.assertNumQueries(expected_queries):
                p.create_children(auto_generate_count=auto_generate_count)
        self.assertEqual(p.children.all().count(), 300_000)

    def test_create_children_with_conflict_causes_extra_rounds(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        # Mock _get_code_uniquifier to force specific codes that will collide
        # This way we test the actual conflict detection logic
        call_count = [0]

        def mock_get_code_uniquifier(code_index, max_index, extra_length=3):
            call_count[0] += 1
            index = str(code_index).zfill(len(str(max_index)))
            # For first 500 codes, use a suffix that we'll pre-create to force conflicts
            if call_count[0] <= 500:
                suffix = "999"  # Will collide with pre-created codes
            else:
                # After conflicts, use unique suffixes
                suffix = str(call_count[0]).zfill(extra_length)
            return f"{index}{suffix}"

        # Pre-create some codes that will conflict with generated ones.
        # Since start_index is prefilled based on existing child count,
        # new codes will start from index 500 (after these 500 pre-created codes).
        # Create codes at indices 500-999 with suffix "999" to conflict with
        # the first 500 generated codes (which start at index 500).
        conflicted_codes = [f"TEST-VOUCHER-{i:05d}999" for i in range(500, 1000)]
        p._create_child_batch(conflicted_codes, update_children=False)
        self.assertEqual(p.children.all().count(), 500)
        with patch.object(
            p, "_get_code_uniquifier", side_effect=mock_get_code_uniquifier
        ):
            # Request 20,000 codes
            # First chunk (10,000 limit) will have 500 conflicts
            # This should trigger the retry logic to generate 500 more codes
            round_chunk_size = 10_000
            auto_generate_count = 20_000
            baseline_num_queries = 3
            insert_batch_size = 1_000
            # Query breakdown:
            # - Round 1: Generate 10,000 codes, 500 conflicts, 9,500 codes collected
            #   1 conflict check query
            # - Round 2: Generate 10,000 more codes, 0 conflict, 10,000 codes collected
            #   1 conflict check query
            # - Round 3: Generate 500 more codes, 0 conflict, 500 codes collected
            #   1 conflict check query
            # - Three rounds' codes (9500 + 10,000 + 500 = 20,000)
            #   20 bulk_create query for all 20,000 codes
            # Total: 3 (baseline) + 3 (conflict checks = round number) + 20 (bulk_create) = 26 queries
            rounds = (
                (auto_generate_count + round_chunk_size - 1) // round_chunk_size
            ) + 1  # ideal case round count plus 1 extra
            bulk_creates = auto_generate_count // insert_batch_size
            expected_queries = baseline_num_queries + rounds + bulk_creates
            with self.assertNumQueries(expected_queries):
                p.create_children(auto_generate_count=auto_generate_count)
        self.assertEqual(
            p.children.all().count(), 20_500
        )  # 500 pre-existing + 20,000 new

    def test_create_child_batch_empty_list(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        created_codes = p._create_child_batch([], update_children=False)
        self.assertEqual(len(created_codes), 0)
        self.assertEqual(p.children.all().count(), 0)

    def test_get_child_code_batch_uniqueness(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        # Generate a batch of codes
        codes = p._get_child_code_batch(2000)
        # All codes should be unique
        self.assertEqual(len(codes), 2000)
        self.assertEqual(len(set(codes)), 2000)

    def test_get_child_code_batch_max_round_iterations_exceeded(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )

        call_count = [0]

        def mock_get_code_uniquifier(code_index, max_index, extra_length=3):
            call_count[0] += 1
            index = str(code_index).zfill(len(str(max_index)))
            # Use call_count to ensure each call returns a different value
            return f"{index}{call_count[0]:03d}"

        # Pre-create vouchers that will collide with codes for indices 0-99
        # across all possible suffix values to cover multiple retry rounds.
        # (simulating a concurrent job that inserted these codes with the same base count)
        # For indices 100-109, we don't create conflicts, so they can succeed.
        # This means out of 110 requested codes, only 10 will succeed per round,
        # and 100 will keep failing, forcing retries until max_rounds is exceeded.
        conflicted_codes = []
        for i in range(100):
            for suffix in range(600):
                conflicted_codes.append(f"TEST-VOUCHER-{i:03d}{suffix:03d}")
        p._create_child_batch(conflicted_codes, update_children=False)

        # Mock the count to return 0 (simulating that we queried before the concurrent job inserted)
        original_filter = p.__class__.objects.filter

        def mock_filter(*args, **kwargs):
            qs = original_filter(*args, **kwargs)
            # Only mock the count for the startswith query (existing child count)
            if "code__startswith" in kwargs:

                class MockQS:
                    def count(self):
                        return 0  # Simulate race condition, we see 0 children

                return MockQS()
            return qs

        with patch.object(p.__class__.objects, "filter", side_effect=mock_filter):
            with patch.object(
                p, "_get_code_uniquifier", side_effect=mock_get_code_uniquifier
            ):
                # For 110 codes with chunk_size=10,000, base_rounds=1, max_rounds=max(5, 1*3)=5
                # Codes for indices 100-109 will succeed, but codes for indices 0-99
                # will always collide (start_index = 0 from mocked count), forcing retries.
                # This continues until max_rounds is exceeded.
                with self.assertRaises(RuntimeError) as cm:
                    p._get_child_code_batch(110)
                self.assertEqual(
                    "Couldn't find enough unique child codes after 5 rounds.",
                    str(cm.exception),
                )

    def test_update_parent(self):
        customer = Group.objects.create(name="Customers")
        csrs = Group.objects.create(name="Customer Service Reps")

        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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

        p.save()
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
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        c2 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        c2 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-x",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )

        # These vouchers shouldn't save
        for i in range(5):
            Voucher.objects.create(
                parent=p,
                name="Test Voucher",
                code=f"test-voucher-{i}",
                usage=Voucher.MULTI_USE,
                start_datetime=timezone.now(),
                end_datetime=timezone.now(),
                limit_usage_by_group=False,
            )

        with self.assertNumQueries(11):
            c1.record_discount({"discount": 5})

    def test_record_discount(self):
        p = Voucher.objects.create(
            name="Test Voucher",
            code="test-voucher",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        c2 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-2",
            usage=Voucher.MULTI_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            limit_usage_by_group=False,
        )
        c1 = Voucher.objects.create(
            parent=p,
            name="Test Voucher",
            code="test-voucher-1",
            usage=Voucher.SINGLE_USE,
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
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

from unittest.mock import patch

from django.contrib.auth.models import User
from django.db.models import Q
from django.test import RequestFactory, TestCase, TransactionTestCase
from oscar.apps.catalogue import models as catalogue_models
from oscar.core.loading import get_class
from oscar.test.factories import create_product, create_stockrecord

from oscarbluelight.offer import models

RangeProductSearchForm = get_class("ranges_dashboard.forms", "RangeProductSearchForm")
RangeProductListView = get_class("ranges_dashboard.views", "RangeProductListView")


class TestWholeSiteRange(TransactionTestCase):
    def setUp(self):
        self.range = models.Range.objects.create(
            name="All products", includes_all_products=True
        )
        self.prod = create_product()
        self.child = create_product(structure="child", parent=self.prod)
        self.category = catalogue_models.Category.add_root(name="root")
        self.prod.categories.add(self.category)

    def test_all_products_range(self):
        self.assertTrue(self.range.contains_product(self.prod))

    def test_whitelisting(self):
        self.range.add_product(self.prod)
        self.assertTrue(self.range.contains_product(self.prod))

    def test_blacklisting(self):
        self.range.excluded_products.add(self.prod)
        self.assertFalse(self.range.contains_product(self.prod))

    def test_category_blacklisting(self):
        self.range.excluded_categories.add(self.category)
        self.assertNotIn(self.range, models.Range.objects.contains_product(self.prod))
        self.assertNotIn(self.range, models.Range.objects.contains_product(self.child))
        self.assertFalse(self.range.contains_product(self.prod))
        self.assertFalse(self.range.contains_product(self.child))
        self.assertNotIn(self.prod, self.range.all_products())
        self.assertNotIn(self.child, self.range.all_products())


class TestChildRange(TransactionTestCase):
    def setUp(self):
        self.range = models.Range.objects.create(
            name="Child-specific range", includes_all_products=False
        )
        self.parent = create_product(structure="parent")
        self.child1 = create_product(structure="child", parent=self.parent)
        self.child2 = create_product(structure="child", parent=self.parent)
        self.range.add_product(self.child1)

    def test_includes_child(self):
        self.assertTrue(self.range.contains_product(self.child1))

    def test_does_not_include_parent(self):
        self.assertFalse(self.range.contains_product(self.parent))

    def test_does_not_include_sibling(self):
        self.assertFalse(self.range.contains_product(self.child2))


class TestPartialRange(TransactionTestCase):
    def setUp(self):
        self.range = models.Range.objects.create(
            name="All products", includes_all_products=False
        )
        self.parent = create_product(structure="parent")
        self.child = create_product(structure="child", parent=self.parent)

    def test_empty_list(self):
        self.assertFalse(self.range.contains_product(self.parent))
        self.assertFalse(self.range.contains_product(self.child))

    def test_included_classes(self):
        self.range.classes.add(self.parent.get_product_class())
        self.assertTrue(self.range.contains_product(self.parent))
        self.assertTrue(self.range.contains_product(self.child))

    def test_includes(self):
        self.range.add_product(self.parent)

        self.assertTrue(self.range.contains_product(self.parent))
        self.assertTrue(self.range.contains_product(self.child))

    def test_included_class_with_exception(self):
        self.range.classes.add(self.parent.get_product_class())
        self.range.excluded_products.add(self.parent)
        self.assertFalse(self.range.contains_product(self.parent))
        self.assertFalse(self.range.contains_product(self.child))

    def test_included_excluded_products_in_all_products(self):
        count = 5
        included_products = [create_product() for _ in range(count)]
        excluded_products = [create_product() for _ in range(count)]

        for product in included_products:
            models.RangeProduct.objects.create(product=product, range=self.range)

        self.range.excluded_products.add(*excluded_products)

        all_products = self.range.all_products()
        self.assertEqual(all_products.count(), count)
        self.assertEqual(self.range.num_products(), count)

        for product in included_products:
            self.assertTrue(product in all_products)

        for product in excluded_products:
            self.assertTrue(product not in all_products)

    def test_product_classes_in_all_products(self):
        product_in_included_class = create_product(product_class="123")
        included_product_class = product_in_included_class.product_class
        excluded_product_in_included_class = create_product(
            product_class=included_product_class.name
        )

        self.range.classes.add(included_product_class)
        self.range.excluded_products.add(excluded_product_in_included_class)

        all_products = self.range.all_products()
        self.assertTrue(product_in_included_class in all_products)
        self.assertTrue(excluded_product_in_included_class not in all_products)

        self.assertEqual(self.range.num_products(), 1)

    def test_categories_in_all_products(self):
        included_category = catalogue_models.Category.add_root(name="root")
        product_in_included_category = create_product()
        excluded_product_in_included_category = create_product()

        catalogue_models.ProductCategory.objects.create(
            product=product_in_included_category, category=included_category
        )
        catalogue_models.ProductCategory.objects.create(
            product=excluded_product_in_included_category, category=included_category
        )

        self.range.included_categories.add(included_category)
        self.range.excluded_products.add(excluded_product_in_included_category)

        all_products = self.range.all_products()
        self.assertTrue(product_in_included_category in all_products)
        self.assertTrue(excluded_product_in_included_category not in all_products)

        self.assertEqual(self.range.num_products(), 1)

    def test_descendant_categories_in_all_products(self):
        parent_category = catalogue_models.Category.add_root(name="parent")
        child_category = parent_category.add_child(name="child")
        grand_child_category = child_category.add_child(name="grand-child")

        c_product = create_product()
        gc_product = create_product()

        catalogue_models.ProductCategory.objects.create(
            product=c_product, category=child_category
        )
        catalogue_models.ProductCategory.objects.create(
            product=gc_product, category=grand_child_category
        )

        self.range.included_categories.add(parent_category)

        all_products = self.range.all_products()
        self.assertTrue(c_product in all_products)
        self.assertTrue(gc_product in all_products)

        self.assertEqual(self.range.num_products(), 2)

    def test_product_duplicated_in_all_products(self):
        """Making sure product is not duplicated in range products if it has multiple categories assigned."""

        included_category1 = catalogue_models.Category.add_root(name="cat1")
        included_category2 = catalogue_models.Category.add_root(name="cat2")
        product = create_product()
        catalogue_models.ProductCategory.objects.create(
            product=product, category=included_category1
        )
        catalogue_models.ProductCategory.objects.create(
            product=product, category=included_category2
        )

        self.range.included_categories.add(included_category1)
        self.range.included_categories.add(included_category2)
        self.range.add_product(product)

        all_product_ids = list(self.range.all_products().values_list("id", flat=True))
        product_occurances_in_range = all_product_ids.count(product.id)
        self.assertEqual(product_occurances_in_range, 1)

    def test_product_remove_from_range(self):
        included_category = catalogue_models.Category.add_root(name="root")
        product = create_product()
        catalogue_models.ProductCategory.objects.create(
            product=product, category=included_category
        )

        self.range.included_categories.add(included_category)
        self.range.add_product(product)

        all_products = self.range.all_products()
        self.assertTrue(product in all_products)

        self.range.remove_product(product)

        all_products = self.range.all_products()
        self.assertFalse(product in all_products)

        # Re-adding product should return it to the products range
        self.range.add_product(product)

        all_products = self.range.all_products()
        self.assertTrue(product in all_products)

    def test_range_is_reordable(self):
        product = create_product()
        self.range.add_product(product)
        self.assertTrue(self.range.is_reorderable)

        included_category = catalogue_models.Category.add_root(name="root")
        catalogue_models.ProductCategory.objects.create(
            product=product, category=included_category
        )
        self.range.included_categories.add(included_category)

        self.range.invalidate_cached_queryset()
        self.assertFalse(self.range.is_reorderable)

        self.range.included_categories.remove(included_category)
        self.range.invalidate_cached_queryset()
        self.assertTrue(self.range.is_reorderable)


class TestRangeModel(TransactionTestCase):
    def test_ensures_unique_slugs_are_used(self):
        first_range = models.Range.objects.create(name="Foo")
        first_range.name = "Bar"
        first_range.save()
        models.Range.objects.create(name="Foo")


class TestRangeAddProductBatch(TransactionTestCase):
    def test_add_product_batch(self):
        # Create some products
        product1 = create_product()
        product2 = create_product()
        product3 = create_product()
        product4 = create_product()

        # Crwate two ranges. Range 2 includes all products by default.
        rng1 = models.Range.objects.create(name="Range 1", includes_all_products=False)
        rng2 = models.Range.objects.create(name="Range 2", includes_all_products=True)

        # Exclude p2 from both ranges
        rng1.excluded_products.add(product2)
        rng2.excluded_products.add(product2)

        # Check starting point. Range 1 contains nothing. Range 2 contains
        # everything except p2.
        self.assertFalse(rng1.contains_product(product1))
        self.assertFalse(rng1.contains_product(product2))
        self.assertFalse(rng1.contains_product(product3))
        self.assertFalse(rng1.contains_product(product4))

        self.assertTrue(rng2.contains_product(product1))
        self.assertFalse(rng2.contains_product(product2))
        self.assertTrue(rng2.contains_product(product3))
        self.assertTrue(rng2.contains_product(product4))

        # Add p1, p2, and p3 to range 1. Should add all 3 products and remove
        # p2 from the exclude list. Should _not_ affect range 2.
        rng1.add_product_batch([product1, product2, product3])

        # Check results. Range 1 should now include p{1,2,3}. Range 2 should
        # include everything except for p2.
        self.assertTrue(rng1.contains_product(product1))
        self.assertTrue(rng1.contains_product(product2))
        self.assertTrue(rng1.contains_product(product3))
        self.assertFalse(rng1.contains_product(product4))

        self.assertTrue(rng2.contains_product(product1))
        self.assertFalse(rng2.contains_product(product2))
        self.assertTrue(rng2.contains_product(product3))
        self.assertTrue(rng2.contains_product(product4))

        # Add p2 back to excluded products
        rng1.excluded_products.add(product2)

        # Check results
        self.assertTrue(rng1.contains_product(product1))
        self.assertFalse(rng1.contains_product(product2))
        self.assertTrue(rng1.contains_product(product3))
        self.assertFalse(rng1.contains_product(product4))

        self.assertTrue(rng2.contains_product(product1))
        self.assertFalse(rng2.contains_product(product2))
        self.assertTrue(rng2.contains_product(product3))
        self.assertTrue(rng2.contains_product(product4))


class TestRangeExcludeProductBatch(TransactionTestCase):
    def test_exclude_product_batch(self):
        # Create some products
        product1 = create_product()
        product2 = create_product()
        product3 = create_product()
        product4 = create_product()

        # Create two ranges.
        rng1 = models.Range.objects.create(name="Range 1", includes_all_products=False)
        rng2 = models.Range.objects.create(name="Range 2", includes_all_products=False)

        # Add p{1,2,3} to both ranges
        rng1.included_products.add(product1)
        rng1.included_products.add(product2)
        rng1.included_products.add(product3)
        rng2.included_products.add(product1)
        rng2.included_products.add(product2)
        rng2.included_products.add(product3)

        # Check starting point. Both ranges contain p{1,2,3}
        self.assertTrue(rng1.contains_product(product1))
        self.assertTrue(rng1.contains_product(product2))
        self.assertTrue(rng1.contains_product(product3))
        self.assertFalse(rng1.contains_product(product4))

        self.assertTrue(rng2.contains_product(product1))
        self.assertTrue(rng2.contains_product(product2))
        self.assertTrue(rng2.contains_product(product3))
        self.assertFalse(rng2.contains_product(product4))

        # Exclude p{1,2,4} from range 1. Should _not_ affect range 2.
        rng1.exclude_product_batch([product1, product2, product4])

        # Check results. Range 1 should now include p{1,2,3}. Range 2 should
        # include everything except for p2.
        self.assertFalse(rng1.contains_product(product1))
        self.assertFalse(rng1.contains_product(product2))
        self.assertTrue(rng1.contains_product(product3))
        self.assertFalse(rng1.contains_product(product4))

        self.assertTrue(rng2.contains_product(product1))
        self.assertTrue(rng2.contains_product(product2))
        self.assertTrue(rng2.contains_product(product3))
        self.assertFalse(rng2.contains_product(product4))


class TestRangeProductListView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username="john", email="test@example.com", password="password"
        )
        # Create a product range
        rng = models.Range.objects.create(name="Products Range", slug="products-range")
        # Create products with different attributes
        self.product1 = create_product(title="Test Product 1", upc="1234567890")
        self.product2 = create_product(title="Different Product", upc="0987654321")
        self.product3 = create_product(title="Special Item", upc="5555555555")
        # Create stock records
        create_stockrecord(product=self.product1, partner_sku="SKU001")
        create_stockrecord(product=self.product2, partner_sku="SKU002")
        create_stockrecord(product=self.product3, partner_sku="SKU003")
        # Add products to range with specific display order
        models.RangeProduct.objects.create(
            range=rng, product=self.product1, display_order=1
        )
        models.RangeProduct.objects.create(
            range=rng, product=self.product2, display_order=2
        )
        models.RangeProduct.objects.create(
            range=rng, product=self.product3, display_order=3
        )
        # Initialize the view
        self.view = RangeProductListView()
        self.view.kwargs = {"pk": rng.pk}

    @staticmethod
    def mock_title_search():
        """
        Mock the Q object to replace `title__search` with `title__icontains`
        as the __search lookup might not properly be configured in test environment db.
        """

        def replace_q(*args, **kwargs):
            if "title__search" in kwargs:
                # Replace lookup
                kwargs["title__icontains"] = kwargs.pop("title__search")
            return Q(*args, **kwargs)

        return patch("oscarbluelight.dashboard.ranges.views.Q", side_effect=replace_q)

    @mock_title_search()
    def test_get_queryset_no_search(self, mock_q):
        request = self.factory.get("/")
        request.user = self.user
        self.view.request = request
        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 3)
        self.assertEqual(list(queryset), [self.product1, self.product2, self.product3])

    @mock_title_search()
    def test_get_queryset_search_by_product_name(self, mock_q):
        request = self.factory.get("/", {"product_name": "Test Product"})
        request.user = self.user
        self.view.request = request
        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.product1)

    @mock_title_search()
    def test_get_queryset_search_by_upc(self, mock_q):
        request = self.factory.get("/", {"upc": "1234567890"})
        request.user = self.user
        self.view.request = request
        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.product1)

    @mock_title_search()
    def test_get_queryset_search_by_sku(self, mock_q):
        request = self.factory.get("/", {"sku": "SKU002"})
        request.user = self.user
        self.view.request = request
        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.product2)

    @mock_title_search()
    def test_get_queryset_multiple_filters(self, mock_q):
        request = self.factory.get(
            "/", {"product_name": "Special", "upc": "5555555555"}
        )
        request.user = self.user
        self.view.request = request
        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.product3)

    @mock_title_search()
    def test_get_queryset_case_insensitive(self, mock_q):
        request = self.factory.get("/", {"product_name": "test PRODUCT"})
        request.user = self.user
        self.view.request = request
        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.product1)

    @mock_title_search()
    def test_get_queryset_no_results(self, mock_q):
        request = self.factory.get("/", {"product_name": "Fake Product"})
        request.user = self.user
        self.view.request = request
        queryset = self.view.get_queryset()
        self.assertEqual(queryset.count(), 0)

    @mock_title_search()
    def test_get_context_data(self, mock_q):
        request = self.factory.get("/", {"product_name": "Different Product"})
        request.user = self.user
        self.view.request = request
        self.view.object_list = self.view.get_queryset()
        self.view.upload_type = ""
        context = self.view.get_context_data()
        self.assertIn("search_form", context)
        self.assertIsInstance(context["search_form"], RangeProductSearchForm)
        self.assertEqual(
            context["search_form"].data.get("product_name"), "Different Product"
        )

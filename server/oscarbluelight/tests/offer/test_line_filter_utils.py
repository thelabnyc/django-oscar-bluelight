"""
Test utility functions for line filtering strategies.
"""

from unittest.mock import Mock

from django.conf import settings
from django.test import TestCase, override_settings

from oscarbluelight.offer.line_filters import DefaultLineFilterStrategy
from oscarbluelight.offer.utils import get_line_filter_strategy


class CustomTestStrategy:
    """A test strategy class defined at module level for testing."""

    def filter_lines(self, offer, basket, line_tuples):
        # Custom logic: reverse the list
        return line_tuples[::-1]


class GetLineFilterStrategyTest(TestCase):
    def test_no_setting_returns_default_strategy(self):
        """When no OSCARBLUELIGHT_LINE_FILTER_STRATEGY setting is provided, should return DefaultLineFilterStrategy."""
        with override_settings():
            # Remove the setting if it exists
            if hasattr(settings, "OSCARBLUELIGHT_LINE_FILTER_STRATEGY"):
                delattr(settings, "OSCARBLUELIGHT_LINE_FILTER_STRATEGY")

            strategy = get_line_filter_strategy()

            self.assertIsInstance(strategy, DefaultLineFilterStrategy)

    def test_empty_setting_returns_default_strategy(self):
        """When OSCARBLUELIGHT_LINE_FILTER_STRATEGY is None, should return DefaultLineFilterStrategy."""
        with override_settings(OSCARBLUELIGHT_LINE_FILTER_STRATEGY=None):
            strategy = get_line_filter_strategy()

            self.assertIsInstance(strategy, DefaultLineFilterStrategy)

    @override_settings(
        OSCARBLUELIGHT_LINE_FILTER_STRATEGY="oscarbluelight.offer.line_filters.DefaultLineFilterStrategy"
    )
    def test_valid_setting_returns_custom_strategy(self):
        """When OSCARBLUELIGHT_LINE_FILTER_STRATEGY is valid, should return that strategy."""
        strategy = get_line_filter_strategy()

        self.assertIsInstance(strategy, DefaultLineFilterStrategy)

    @override_settings(
        OSCARBLUELIGHT_LINE_FILTER_STRATEGY="oscarbluelight.offer.line_filters.BaseLineFilterStrategy"
    )
    def test_valid_base_strategy_import(self):
        """Test importing BaseLineFilterStrategy works correctly."""
        from oscarbluelight.offer.line_filters import BaseLineFilterStrategy

        strategy = get_line_filter_strategy()

        self.assertIsInstance(strategy, BaseLineFilterStrategy)
        # It should be specifically the BaseLineFilterStrategy, not DefaultLineFilterStrategy
        self.assertEqual(type(strategy).__name__, "BaseLineFilterStrategy")

    def test_caching_behavior(self):
        """Test that the function returns consistent instances (no explicit caching required in spec, but good to test)."""
        with override_settings(OSCARBLUELIGHT_LINE_FILTER_STRATEGY=None):
            strategy1 = get_line_filter_strategy()
            strategy2 = get_line_filter_strategy()

            # Should be same class but may be different instances (no caching requirement)
            self.assertEqual(type(strategy1), type(strategy2))

    def test_custom_strategy_class_can_be_loaded(self):
        """Test that a custom strategy class can be loaded and used."""

        # Use the module-level test class
        module_path = f"{CustomTestStrategy.__module__}.{CustomTestStrategy.__name__}"

        with override_settings(OSCARBLUELIGHT_LINE_FILTER_STRATEGY=module_path):
            strategy = get_line_filter_strategy()

            # Test that we got the right type
            self.assertEqual(type(strategy).__name__, "CustomTestStrategy")

            # Test that the custom behavior works
            mock_offer, mock_basket = Mock(), Mock()
            line_tuples = [(1, "a"), (2, "b"), (3, "c")]

            result = strategy.filter_lines(mock_offer, mock_basket, line_tuples)
            expected = [(3, "c"), (2, "b"), (1, "a")]
            self.assertEqual(result, expected)

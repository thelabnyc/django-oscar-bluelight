from unittest import skipIf
from oscar.core.loading import get_model
from .base import SplinterSeleniumTestCase
from . import SKIP_SELENIUM_TESTS

Range = get_model('offer', 'Range')
Condition = get_model('offer', 'Condition')


@skipIf(SKIP_SELENIUM_TESTS, "Skipping Selenium Tests")
class ConditionDashboardTest(SplinterSeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.range = Range.objects.create(name='All Products', includes_all_products=True)


    def test_condition_list(self):
        self._visit('dashboard:condition-list')
        self._take_screenshot('condition-list-0')

        Condition.objects.create(
            range=self.range,
            proxy_class='oscarbluelight.offer.conditions.BluelightCountCondition',
            value=1)

        self.browser.reload()
        self._take_screenshot('condition-list-1')

        Condition.objects.create(
            range=self.range,
            proxy_class='oscarbluelight.offer.conditions.BluelightValueCondition',
            value=100)

        self.browser.reload()
        self._take_screenshot('condition-list-2')


    def test_create_normal_condition(self):
        self._visit('dashboard:condition-list')
        self._take_screenshot('condition-create-normal-0')

        self.browser.find_by_id('condition-create-standard').click()
        self._take_screenshot('condition-create-normal-1')

        self._select_fancy('range', 'All Products')
        self._select_fancy('proxy_class', 'Depends on tax-exclusive value of items')
        self.browser.fill('value', '100')
        self._take_screenshot('condition-create-normal-2')

        self.browser.find_by_css('button[type="submit"]').click()
        self._take_screenshot('condition-create-normal-3')


    def test_create_compound_condition(self):
        Condition.objects.create(
            range=self.range,
            proxy_class='oscarbluelight.offer.conditions.BluelightCountCondition',
            value=1)

        Condition.objects.create(
            range=self.range,
            proxy_class='oscarbluelight.offer.conditions.BluelightValueCondition',
            value=100)

        self._visit('dashboard:condition-list')
        self._take_screenshot('condition-create-compound-0')

        self.browser.find_by_id('condition-create-compound').click()
        self._take_screenshot('condition-create-compound-1')

        self._select_fancy('conjunction', 'OR')
        self._take_screenshot('condition-create-compound-2')

        self._select_fancy('subconditions', '1 item')
        self._take_screenshot('condition-create-compound-3')

        self._select_fancy('subconditions', '100')
        self._take_screenshot('condition-create-compound-4')

        self.browser.find_by_css('button[type="submit"]').click()
        self._take_screenshot('condition-create-compound-5')

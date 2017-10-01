from decimal import Decimal as D
from unittest import skipIf
# from oscar.core.loading import get_model
from .base import SplinterSeleniumTestCase
from . import SKIP_SELENIUM_TESTS
# from selenium.webdriver.common.keys import Keys
from oscarbluelight.offer.models import Condition, Range, Benefit

# Range = get_model('offer', 'Range')
# Condition = get_model('offer', 'Condition')
# ConditionalOffer = get_model('offer', 'ConditionalOffer')


@skipIf(SKIP_SELENIUM_TESTS, "Skipping Selenium Tests")
class ShortNameDashboardTest(SplinterSeleniumTestCase):
    def setUp(self):
        super().setUp()

    def test_short_name_saved(self):

        # Create some defaults
        all_products = Range()
        all_products.includes_all_products = True
        all_products.save()

        condition = Condition()
        condition.proxy_class = 'oscarbluelight.offer.conditions.BluelightValueCondition'
        condition.value = D('15.00')
        condition.range = all_products
        condition.save()
        benefit = Benefit()
        benefit.proxy_class = 'oscarbluelight.offer.benefits.BluelightShippingFixedPriceBenefit'
        benefit.value = 0
        benefit.save()

        # Create new offer
        self._visit_raw('/dashboard/offers/new/name-and-description/')
        self._take_screenshot('short-name-1')

        # Fill in first step
        self.browser.fill('name', 'offer 1 name')
        self.browser.fill('short_name', 'offer 1 short name')
        # TODO how to fill fancy textarea
        # self.browser.find_by_xpath('//*[@id="id_description"]').first.fill('offer 1 description')
        # textarea = self.browser.find_by_xpath('//textarea[not(@readonly)]').first
        # textarea = self.browser.find_by_xpath('//*[@id="tinymce"]')
        # textarea = self.browser.find_by_xpath('//*[@id="id_description_ifr"]').first
        self.browser.fill('priority', '0')
        # el1 = self.browser.find_by_xpath('//select[@name="offer_group"]/option[2]').first
        # print('VVV condition option: [%s]' % el1.outer_html)
        self._select_fancy('offer_group', 'post-tax-offers (priority 1000)')

        # self.browser.fill('priority', '0')
        go_step2_btn = self.browser.find_by_text('Continue to step 2')
        self._take_screenshot('short-name-2')

        go_step2_btn.click()
        self._take_screenshot('short-name-3')

        # Fill in second step
        self._select_fancy('benefit', 'Get shipping for $0.00')
        self._take_screenshot('short-name-4')
        go_step3_btn = self.browser.find_by_text('Continue to step 3').first
        go_step3_btn.click()
        self._take_screenshot('short-name-5')

        # Fill in third step
        # Select condition
        # el1 = self.browser.find_by_xpath('//select[@name="condition"]/option[2]').first
        # print('VVV condition option: %s' % el1.outer_html)
        self._select_fancy('condition', 'Basket includes $15.00 (tax-exclusive) from ')
        self._take_screenshot('short-name-6')
        go_step4_btn = self.browser.find_by_text('Continue to step 4').first
        go_step4_btn.click()
        self._take_screenshot('short-name-7')

        # Fill in fourth step
        save_offer_btn = self.browser.find_by_text('Save this offer').first
        save_offer_btn.click()
        self._take_screenshot('short-name-8')

        # Verify the short name is there
        el = self.browser.find_by_xpath('//*[@id="default"]/div[1]/div/div[3]/table[2]/tbody/tr[2]')
        self.assertEqual('Short Name offer 1 short name', el.text)

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from splinter import Browser
import socket
import os


class SplinterSeleniumTestCase(StaticLiveServerTestCase):

    # Need this to rstore the database to initial state after each test
    serialized_rollback = True

    @classmethod
    def setUpClass(cls):
        # For Django >=1.11, set the server host
        cls.host = socket.gethostname()
        # For Django <=1.10, set the server host
        os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = "{}:8081-8179".format(cls.host)
        super().setUpClass()

    def setUp(self):
        super().setUp()
        User.objects.create_user(
            username="splinter", password="splinter", is_staff=True, is_superuser=True
        )
        self.browser = Browser(
            driver_name="remote", url="http://selenium:4444/wd/hub", browser="chrome"
        )
        self._do_login()

    def tearDown(self):
        super().tearDown()
        self.browser.quit()

    def assertTextIsPresent(self, text):
        self.assertTrue(self.browser.is_text_present(text))

    def assertTextIsNotPresent(self, text):
        self.assertFalse(self.browser.is_text_present(text))

    def _build_url(self, name):
        path = reverse(name)
        return "{}{}".format(self.live_server_url, path)

    def _visit(self, name):
        url = self._build_url(name)
        self.browser.visit(url)

    def _visit_raw(self, name):
        url = "{}{}".format(self.live_server_url, name)
        self.browser.visit(url)

    def _do_login(self):
        self._visit("dashboard:login")

        self.assertTextIsPresent("Oscar")

        self.browser.fill("username", "splinter")
        self.browser.fill("password", "splinter")
        self.browser.find_by_css('input[type="submit"]').click()

        self.assertTextIsNotPresent("Please enter a correct username and password.")
        self.assertTextIsPresent("Profile")

    def _take_screenshot(self, name):
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "screenshots", "{}.png".format(name))
        self.browser.driver.save_screenshot(path)

    def _select_fancy(self, select_id, option_text):
        """
        Handle selecting an option from the fancy JavaScript select used by Oscar Dashboard
        """
        self.browser.find_by_id("s2id_id_{}".format(select_id)).click()
        autocomplete = None
        for elem in self.browser.find_by_css(".select2-input"):
            if elem.visible:
                autocomplete = elem
                break
        autocomplete.type(option_text)
        autocomplete.type("\n")

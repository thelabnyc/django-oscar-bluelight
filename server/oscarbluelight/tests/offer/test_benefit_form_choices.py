from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django_redis import get_redis_connection

from oscarbluelight.dashboard.offers.forms import BenefitForm, BenefitSearchForm
from oscarbluelight.offer.models import Benefit

COMPOUND_BENEFIT_CPATH = "oscarbluelight.offer.benefits.CompoundBenefit"


class BenefitFormChoicesTest(TestCase):
    """
    Regression tests: BenefitSearchForm must not pollute the shared
    settings.BLUELIGHT_BENEFIT_CLASSES list with its "Compound Benefit" filter
    entry, because BenefitForm builds its create-form choices from the same
    list. Offering "Compound Benefit" on the plain create form let staff save a
    base Benefit row with a compound proxy_class and no MTI child row.
    """

    def setUp(self):
        conn = get_redis_connection("redis")
        conn.flushall()
        self.client = Client()
        self.user = User.objects.create_user(
            "admin",
            "admin@test.com",
            "password",
            is_staff=True,
            is_superuser=True,
        )

    def test_settings_list_not_polluted_by_import(self):
        setting_cpaths = [choice[0] for choice in settings.BLUELIGHT_BENEFIT_CLASSES]
        self.assertNotIn(COMPOUND_BENEFIT_CPATH, setting_cpaths)

    def test_create_form_omits_compound_choice(self):
        choices = [choice[0] for choice in BenefitForm().fields["proxy_class"].choices]
        self.assertNotIn(COMPOUND_BENEFIT_CPATH, choices)

    def test_search_form_offers_compound_choice(self):
        choices = [
            choice[0] for choice in BenefitSearchForm().fields["benefit_type"].choices
        ]
        self.assertIn(COMPOUND_BENEFIT_CPATH, choices)

    def test_create_view_does_not_create_compound_orphan(self):
        # The create form must reject the compound proxy_class, so posting it
        # cannot write a base Benefit row with a compound proxy_class (the
        # orphan that 500s the benefits/ranges pages).
        client = Client(raise_request_exception=False)
        client.login(username="admin", password="password")
        response = client.post(
            reverse("dashboard:benefit-create"),
            data={"proxy_class": COMPOUND_BENEFIT_CPATH, "value": "10"},
        )
        self.assertNotEqual(response.status_code, 302)
        self.assertFalse(
            Benefit.objects.filter(proxy_class=COMPOUND_BENEFIT_CPATH).exists()
        )

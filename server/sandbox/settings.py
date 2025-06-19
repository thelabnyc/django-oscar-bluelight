from fnmatch import fnmatch
import os
import sys

from django.utils.translation import gettext_lazy as _
from oscar.defaults import *  # noqa
import django_stubs_ext

from oscarbluelight.defaults import *  # NOQA

django_stubs_ext.monkeypatch()


class glob_list(list[str]):
    def __contains__(self, key: object) -> bool:
        for elt in self:
            if isinstance(key, str) and fnmatch(key, elt):
                return True
        return False


IS_UNIT_TEST = "test" in sys.argv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIRTUAL_ENV = os.environ.get("VIRTUAL_ENV", "").split("/").pop()
CI_JOB_ID = os.environ.get("CI_JOB_ID", "0")

DEBUG = True
SECRET_KEY = "li0$-gnv)76g$yf7p@(cg-^_q7j6df5cx$o-gsef5hd68phj!4"
SITE_ID = 1
ROOT_URLCONF = "sandbox.urls"
ALLOWED_HOSTS = ["*"]

INTERNAL_IPS = glob_list(["127.0.0.1", "172.17.*.*", "192.168.*.*", "10.0.*.*"])

USE_I18N = True
LANGUAGE_CODE = "en-us"
LANGUAGES = (
    ("en-us", _("English")),
    ("es", _("Spanish")),
)

# Configure JUnit XML output
TEST_RUNNER = "xmlrunner.extra.djangotestrunner.XMLTestRunner"
_tox_env_name = os.environ.get("TOX_ENV_NAME")
if _tox_env_name:
    TEST_OUTPUT_DIR = os.path.join(BASE_DIR, f"../../junit-{_tox_env_name}/")
else:
    TEST_OUTPUT_DIR = os.path.join(BASE_DIR, "../../junit/")

INSTALLED_APPS = [
    # Core Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.flatpages",
    # Bluelight. Must come before `django-oscar` so that template inheritance / overrides work correctly.
    "oscarbluelight",
    # django-oscar
    "oscar.config.Shop",
    "oscar.apps.analytics.apps.AnalyticsConfig",
    "oscar.apps.checkout.apps.CheckoutConfig",
    "oscar.apps.address.apps.AddressConfig",
    "oscar.apps.shipping.apps.ShippingConfig",
    "oscar.apps.catalogue.apps.CatalogueConfig",
    "oscar.apps.catalogue.reviews.apps.CatalogueReviewsConfig",
    "oscar.apps.communication.apps.CommunicationConfig",
    "sandbox.partner.apps.PartnerConfig",  # sandbox.partner.apps.PartnerConfig
    "sandbox.basket.apps.BasketConfig",  # sandbox.basket.apps.BasketConfig
    "oscar.apps.payment.apps.PaymentConfig",
    "oscarbluelight.offer.apps.OfferConfig",  # oscar.apps.offer.apps.OfferConfig
    "oscar.apps.order.apps.OrderConfig",
    "oscar.apps.customer.apps.CustomerConfig",
    "oscar.apps.search.apps.SearchConfig",
    "oscarbluelight.voucher.apps.VoucherConfig",  # oscar.apps.voucher.apps.VoucherConfig
    "oscar.apps.wishlists.apps.WishlistsConfig",
    "oscar.apps.dashboard.apps.DashboardConfig",
    "oscar.apps.dashboard.reports.apps.ReportsDashboardConfig",
    "oscar.apps.dashboard.users.apps.UsersDashboardConfig",
    "oscar.apps.dashboard.orders.apps.OrdersDashboardConfig",
    "oscar.apps.dashboard.catalogue.apps.CatalogueDashboardConfig",
    "oscarbluelight.dashboard.offers.apps.OffersDashboardConfig",  # oscar.apps.dashboard.offers.apps.OffersDashboardConfig
    "oscar.apps.dashboard.partners.apps.PartnersDashboardConfig",
    "oscar.apps.dashboard.pages.apps.PagesDashboardConfig",
    "oscarbluelight.dashboard.ranges.apps.RangesDashboardConfig",  # "oscar.apps.dashboard.ranges.apps.RangesDashboardConfig",
    "oscar.apps.dashboard.reviews.apps.ReviewsDashboardConfig",
    "oscarbluelight.dashboard.vouchers.apps.VouchersDashboardConfig",  # oscar.apps.dashboard.vouchers.apps.VouchersDashboardConfig
    "oscar.apps.dashboard.communications.apps.CommunicationsDashboardConfig",
    "oscar.apps.dashboard.shipping.apps.ShippingDashboardConfig",
    # 3rd-party apps that oscar depends on
    "widget_tweaks",
    # "haystack",
    "treebeard",
    "sorl.thumbnail",
    "django_tables2",
    # 3rd-party apps we depend on
    "rest_framework",
    "thelabdb.pgviews",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "oscar.apps.basket.middleware.BasketMiddleware",
]

if not IS_UNIT_TEST:
    INSTALLED_APPS += [
        "debug_toolbar",
    ]
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE


AUTHENTICATION_BACKENDS = (
    "oscar.apps.customer.auth_backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "oscar.apps.search.context_processors.search_form",
                "oscar.apps.checkout.context_processors.checkout",
                "oscar.apps.communication.notifications.context_processors.notifications",
                "oscar.core.context_processors.metadata",
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "",
        "HOST": "postgres",
        "PORT": 5432,
    }
}

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.simple_backend.SimpleEngine",
    },
}


_redis_db = 0
_redis_max_dbs = 16
if IS_UNIT_TEST:
    _redis_db = os.getpid() % _redis_max_dbs
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "oscarbluelight-testing-sandbox",
        "KEY_PREFIX": VIRTUAL_ENV,
    },
    "redis": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://redis:6379/{_redis_db}",
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "timeout": 20,
            },
        },
        "KEY_PREFIX": VIRTUAL_ENV,
    },
}
REDIS_CACHE_ALIAS = "redis"

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), "../tmp/static/")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), "../tmp/media/")

OSCAR_DEFAULT_CURRENCY = "USD"
OSCARAPI_BLOCK_ADMIN_API_ACCESS = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Celery Config
CELERY_TASK_ALWAYS_EAGER = True

# Django Tasks Config
TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
    },
}

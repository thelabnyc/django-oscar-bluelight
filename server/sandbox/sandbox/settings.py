from django.utils.translation import gettext_lazy as _
from oscar.defaults import *  # noqa
from oscarbluelight.defaults import *  # NOQA
from fnmatch import fnmatch
import os
import sys


class glob_list(list):
    def __contains__(self, key):
        for elt in self:
            if fnmatch(key, elt):
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
    "oscar",
    "oscar.apps.analytics",
    "oscar.apps.communication",
    "oscar.apps.checkout",
    "oscar.apps.address",
    "oscar.apps.shipping",
    "oscar.apps.catalogue",
    "oscar.apps.catalogue.reviews",
    "sandbox.partner",  # 'oscar.apps.partner',
    "sandbox.basket",  # 'oscar.apps.basket',
    "oscar.apps.payment",
    "oscarbluelight.offer",  # 'oscar.apps.offer',
    "oscar.apps.order",
    "oscar.apps.customer",
    "oscar.apps.search",
    "oscarbluelight.voucher",  # 'oscar.apps.voucher',
    "oscar.apps.wishlists",
    "oscar.apps.dashboard",
    "oscar.apps.dashboard.reports",
    "oscar.apps.dashboard.users",
    "oscar.apps.dashboard.orders",
    "oscar.apps.dashboard.catalogue",
    "oscarbluelight.dashboard.offers",  # 'oscar.apps.dashboard.offers',
    "oscar.apps.dashboard.partners",
    "oscar.apps.dashboard.pages",
    "oscar.apps.dashboard.ranges",
    "oscar.apps.dashboard.reviews",
    "oscarbluelight.dashboard.vouchers",  # 'oscar.apps.dashboard.vouchers',
    "oscar.apps.dashboard.communications",
    "oscar.apps.dashboard.shipping",
    # 3rd-party apps that oscar depends on
    "widget_tweaks",
    # "haystack",
    "treebeard",
    "sorl.thumbnail",
    "django_tables2",
    # 3rd-party apps we depend on
    "rest_framework",
    "django_pgviews",
    # Dev/Debug stuff
    "debug_toolbar",
]

MIDDLEWARE = (
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "oscar.apps.basket.middleware.BasketMiddleware",
)

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
        "ENGINE": "django.db.backends.postgresql_psycopg2",
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

def get_redis_parser_class():
    try:
        from redis.connection import _HiredisParser
        return "redis.connection._HiredisParser"
    except ImportError:
        return "redis.connection.HiredisParser"

redis_parser_class = get_redis_parser_class()

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
        "LOCATION": "redis://redis:6379/{}".format(_redis_db),
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "timeout": 20,
            },
            "PARSER_CLASS": redis_parser_class,
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

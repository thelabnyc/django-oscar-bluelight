from distutils.util import strtobool
import os

SKIP_SELENIUM_TESTS = strtobool(os.environ.get('SKIP_SELENIUM_TESTS', 'no'))

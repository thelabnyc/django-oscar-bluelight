#!/usr/bin/env python
from setuptools import setup, find_packages, Distribution
import codecs
import os.path

# Make sure versiontag exists before going any further
Distribution().fetch_build_eggs("versiontag>=1.2.0")

from versiontag import get_version, cache_git_tag  # NOQA


packages = find_packages("src")

install_requires = [
    "celery>=4.3",
    "Django>=3.2",
    "django-oscar>=3.1b0",
    "django-redis>=4.8.0",
    "django-pgviews>=0.5.7",
    "djangorestframework>=3.11",
    "psycopg2-binary>=2.8.4",
    "redis>=3.0.0",
]

extras_require = {
    "development": [
        "coverage>=4.4.2",
        "django-debug-toolbar>=3.2.1",
        "flake8>=3.2.1",
        "hiredis>=0.2.0",
        "sorl-thumbnail>=11.04",
        "sphinx>=1.5.2",
        "splinter>=0.7.5",
        "tox>=2.6.0",
        "unittest-xml-reporting>=3.0.4",
        "versiontag>=1.2.0",
    ],
}


def fpath(name):
    return os.path.join(os.path.dirname(__file__), name)


def read(fname):
    return codecs.open(fpath(fname), encoding="utf-8").read()


cache_git_tag()

setup(
    name="django-oscar-bluelight",
    description="Bluelight Specials - Enhancements to the offer and vouchers features for Django Oscar.",
    version=get_version(pypi=True),
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    author="Craig Weber",
    author_email="crgwbr@gmail.com",
    url="https://gitlab.com/thelabnyc/django-oscar-bluelight",
    license="ISC",
    package_dir={"": "src"},
    packages=packages,
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
)

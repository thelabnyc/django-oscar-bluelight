#!/usr/bin/env python
import codecs
import os.path
from setuptools import setup
from versiontag import get_version, cache_git_tag


packages = [
    'oscarbluelight',
    'oscarbluelight.dashboard',
    'oscarbluelight.dashboard.offers',
    'oscarbluelight.dashboard.vouchers',
    'oscarbluelight.offer',
    'oscarbluelight.offer.migrations',
    'oscarbluelight.tests',
    'oscarbluelight.tests.offer',
    'oscarbluelight.tests.voucher',
    'oscarbluelight.voucher',
    'oscarbluelight.voucher.migrations',
]

setup_requires = [
    'versiontag>=1.1.0',
]

requires = [
    'Django>=1.9.6',
    'django-oscar>=1.2.1',
]

def fpath(name):
    return os.path.join(os.path.dirname(__file__), name)

def read(fname):
    return codecs.open(fpath(fname), encoding='utf-8').read()

cache_git_tag()

setup(
    name='django-oscar-bluelight',
    description="Bluelight Specials - Enhancements to the offer and vouchers features for Django Oscar.",
    version=get_version(pypi=True),
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    author='Craig Weber',
    author_email='crgwbr@gmail.com',
    url='https://gitlab.com/thelabnyc/django-oscar-bluelight',
    license='ISC',
    packages=packages,
    include_package_data=True,
    install_requires=requires,
    setup_requires=setup_requires
)

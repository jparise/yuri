#!/usr/bin/env python

from distutils.core import setup

version = __import__('yuri').__version__

setup(
    name = 'Yuri',
    version = version,
    description = 'URI Manipulation Library',
    author = 'Jon Parise',
    author_email = 'jon@indelible.org',
    license = "MIT License",
    classifiers = ['Intended Audience :: Developers',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python'],
    py_modules = ['yuri'],
)

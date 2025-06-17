#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ 'hid' ]

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Steve Randall",
    author_email='steve@mylastname.cc',
    python_requires='~=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Service to talk to cheap USB-HID Watchdog Timers",
    entry_points={
        'console_scripts': [
            'hid_watchdog=hid_watchdog.cli:main',
        ],
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='hid_watchdog',
    name='hid_watchdog',
    packages=find_packages(include=['hid_watchdog', 'hid_watchdog.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/technotaff/hid_watchdog',
    version='0.1.7',
    zip_safe=False,
)

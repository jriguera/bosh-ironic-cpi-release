#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Setuptools module for ironic_cpi

See:
	https://packaging.python.org/en/latest/distributing.html
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
from pip.download import PipSession
from pip.req import parse_requirements



here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
long_description = None
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# parse_requirements() returns generator of pip.req.InstallRequirement objects
reqs = parse_requirements("requirements.txt", session=PipSession())
install_reqs = [str(ir.req) for ir in reqs]

# parse_requirements() returns generator of pip.req.TestRequirement objects
reqs = parse_requirements("test-requirements.txt", session=PipSession())
test_reqs = [str(tr.req) for tr in reqs]

setup(
    name="ironic_cpi",
    url="https://github.com/jriguera/bosh-ironic-cpi-release",
    version="0.1.0",
    keywords='bosh cloudfoundry cpi ironic openstack',
    description="BOSH CPI for Ironic",
    long_description=long_description,
    author="Jose Riguera Lopez",
    author_email="jriguera@gmail.com",
    license='MIT',
    packages=find_packages(exclude=['docs', 'tests']),
    
    # Include additional files into the package
    include_package_data=True,
    package_data={'ironic_cpi': ['logging.ini']},

    # additional files need to be installed into
    data_files=[('config', ['ironic.cfg.sample'])],

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 1 - Alpha',
        # Indicate who your project is intended for
        'Intended Audience :: Bosh CPI',
        'Topic :: Infrastructure Management :: Build Tools',
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7'
    ],

    # Dependent packages (distributions)
    install_requires=install_reqs,
    #test_suite = 'nose.collector',
    tests_require=test_reqs,

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'ironic_cpi=ironic_cpi.__main__:main'
        ],
    }
)

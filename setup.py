#!/usr/bin/env python
import re
from os import path as op

from setuptools import setup


def _read(fname):
    try:
        return open(op.join(op.dirname(__file__), fname)).read()
    except IOError:
        return ''

_meta = _read('graphite_beacon/__init__.py')
_license = re.search(r'^__license__\s*=\s*"(.*)"', _meta, re.M).group(1)
_version = re.search(r'^__version__\s*=\s*"(.*)"', _meta, re.M).group(1)

install_requires = [
    l for l in _read('requirements.txt').split('\n') if l and not l.startswith('#')]

setup(
    name='graphite_beacon',
    version=_version,
    license=_license,
    description=_read('DESCRIPTION'),
    long_description=_read('README.md'),
    platforms=('Any'),
    keywords="graphite alerts monitoring system".split(), # noqa

    author='Kirill Klenov',
    author_email='horneds@gmail.com',
    url='http://github.com/klen/graphite-beacon',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Natural Language :: Russian',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities',
    ],

    packages=['graphite_beacon'],
    include_package_data=True,
    install_requires=install_requires,
    entry_points={'console_scripts': ['graphite-beacon = graphite_beacon.app:run']},
)

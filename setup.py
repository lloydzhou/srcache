#!/usr/bin/env python
import os

from srcache import __version__

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

f = open(os.path.join(os.path.dirname(__file__), 'README.md'))
long_description = f.read()
f.close()

setup(
    name='srcache',
    version=__version__,
    description='Python Stale Cache depends on tornado and redis',
    long_description=long_description,
    url='http://github.com/lloydzhou/StaleRedisCache',
    author='Lloyd Zhou',
    author_email='lloydzhou@qq.com',
    maintainer='Lloyd Zhou',
    maintainer_email='lloydzhou@qq.com',
    keywords=['Stale Cache', 'Redis', 'Tornado'],
    license='MIT',
    packages=['srcache'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        ]
)

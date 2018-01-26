#!/usr/bin/env python
# coding=utf-8

__version__ = '1.0'
VERSION = tuple(map(int, __version__.split('.')))

from .srcache import client, stalecache

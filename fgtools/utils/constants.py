#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import os
from appdirs import user_cache_dir
from importlib.metadata import version

HOME = os.environ.get("HOME", os.path.expanduser("~"))
CACHEDIR = os.environ.get("FGTOOLS_CACHEDIR", user_cache_dir("fgtools", "TheEagle"))
os.makedirs(CACHEDIR, exist_ok=True)
__versionstr__ = version("fgtools")
__version__ = __versionstr__.split(".")


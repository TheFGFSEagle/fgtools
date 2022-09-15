#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import os
from appdirs import user_cache_dir

HOME = os.environ.get("HOME", os.path.expanduser("~"))
CACHEDIR = os.environ.get("FGTOOLS_CACHEDIR", user_cache_dir("fgtools", "TheEagle"))
os.makedirs(CACHEDIR, exist_ok=True)
__version__ = (1, 0, 0)
__versionstr__ = ".".join(map(str, __version__))


#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import os
import sys

HOME = os.environ.get("HOME", os.path.expanduser("~"))
SCRIPTS = ["process-shapefiles.py", "process-elevations.py"]
MODULE = "tgtools"
__version__ = (1, 0, 0)
__versionstr__ = ".".join(map(str, __version__))


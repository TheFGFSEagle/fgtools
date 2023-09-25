#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math
from math import *

from .rectangle import Rectangle
from .coord import Coord
from fgtools.utils import isiterable

_round = round

def round(x, multiple=1):
	return _round(x / multiple) * multiple

def floor(x, multiple=1):
	return math.floor(x / multiple) * multiple

def ceil(x, multiple=1):
	return math.ceil(x / multiple) * multiple

def dist(a, b):
	if not isiterable(a):
		a = [a]
	if not isiterable(b):
		b = [b]
	return math.dist(a, b)


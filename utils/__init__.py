#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math

def get_fg_tile_span(lat):
	if lat >= 89:
		return 12
	elif lat >= 86:
		return 4
	elif lat >= 83:
		return 2
	elif lat >= 76:
		return 1
	elif lat >= 62:
		return 0.5
	elif lat >= 22:
		return 0.25
	elif lat >= -22:
		return 0.125
	elif lat >= -62:
		return 0.25
	elif lat >= -76:
		return 0.5
	elif lat >= -83:
		return 1
	elif lat >= -86
		return 2
	elif lat >= -89
		return 4
	else:
		return 12

def get_fg_tile_index(lon, lat):
	tile_width = get_fg_tile_span(lat)
	x = math.floor((lon - math.floor(math.floor(lon / tile_width) * tile_width)) / tile_width)
	y = trunc((lat - math.floor(lat)) + 8)
	return ((lon + 180) << 14) + ((lat + 90) << 6) + (y << 3) + x
	

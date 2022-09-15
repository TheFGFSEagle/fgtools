#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math
import os
import sys
import subprocess

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
	elif lat >= -86:
		return 2
	elif lat >= -89:
		return 4
	else:
		return 12

def get_fg_tile_index(dlon, dlat):
	tile_width = get_fg_tile_span(dlat)
	lon = math.floor(dlon)
	lat = math.floor(dlat)
	if tile_width <= 1:
		x = math.floor((dlon - lon) / tile_width)
	else:
		lon = int(math.floor(lon / tile_width) * tile_width)
		x = 0
	
	if lat == 90:
		lat = 89
		y = 7
	else:
		y = math.floor((dlat - math.floor(dlat)) * 8)
	
	return ((lon + 180) << 14) + ((lat + 90) << 6) + (y << 3) + x

def get_fg_tile_coords(index):
	lon = index >> 14;
	index -= lon << 14;
	lon -= 180;

	lat = index >> 6;
	index -= lat << 6;
	lat -= 90;
	
	return lon, lat

def get_fg_tile_path(lon, lat):
	top_lon = int(lon / 10);
	main_lon = int(lon);
	if (lon < 0) and (top_lon * 10 != lon):
		top_lon -= 1;
	top_lon *= 10
	if top_lon >= 0:
		hem = "e"
	else:
		hem = "w"
		top_lon *= -1;
	if main_lon < 0:
		main_lon *= -1
	
	top_lat = int(lat / 10)
	main_lat = int(lat)
	if (lat < 0) and (top_lat * 10 != lat):
		top_lat -= 1
	top_lat *= 10
	if top_lat >= 0:
		pole = "n"
	else:
		pole = "s"
		top_lat *= -1
	if main_lat < 0:
		main_lat *= -1
	
	return f"{hem}{int(top_lon):03d}{pole}{int(top_lat):02d}/{hem}{int(main_lon):03d}{pole}{int(main_lat):02d}/{get_fg_tile_index(lon, lat)}"

def make_fgelev_pipe(fgelev, fgscenery, fgdata):
	print("Creating pipe to fgelev … ", end="")
	sys.stdout.flush()
	env = os.environ.copy()
	env["FG_SCENERY"] = os.pathsep.join(fgscenery)
	env["FG_ROOT"] = fgdata
	pipe = subprocess.Popen(args=[fgelev, "--expire", "1"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	pipe.stdout.flush()
	pipe.stdout.readline()
	pipe.stdin.flush()
	pipe.stdin.flush()
	print("done")
	return pipe

def isiterable(o, striterable=False):
	if isinstance(o, str):
		return striterable
	else:
		try:
			iter(o)
			return True
		except TypeError:
			return False

def wrap_period(n, min, max):
	while n > max:
		n -= max - min
	
	while n < min:
		n += max - min
	
	return n


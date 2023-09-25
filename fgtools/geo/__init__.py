#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math
import numbers
import typing

from plum import dispatch

from .rectangle import Rectangle
from .coord import Coord
from fgtools.utils import range
from fgtools import math as fgmath

EARTH_RADIUS = 6378138.12
FG_TILE_HEIGHT = 0.125

@dispatch
def get_fg_tile_span(lat: numbers.Real) -> numbers.Real:
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

@dispatch
def get_fg_tile_span(coord: Coord) -> numbers.Real:
	return get_fg_tile_span(coord.lat)

@dispatch
def get_fg_tile_index(dlon: numbers.Real, dlat: numbers.Real) -> int:
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

@dispatch
def get_fg_tile_index(coord: Coord) -> int:
	return get_fg_tile_index(coord.llon, coord.lat)

@dispatch
def get_fg_tile_coords(index: numbers.Real) -> Coord:
	lon = index >> 14;
	index -= lon << 14;
	lon -= 180;
	
	lat = index >> 6;
	index -= lat << 6;
	lat -= 90;
	
	y = index >> 3
	index -= y << 3
	
	x = index
	
	lat += FG_TILE_HEIGHT * y
	lon += get_fg_tile_span(lat) * x
	return Coord(lon, lat)

@dispatch
def get_fg_tile_bbox(lon: numbers.Real, lat: numbers.Real) -> Rectangle:
	rect = Rectangle(0, 0, 0, 0)
	rect.set_left(lon)
	rect.set_bottom(lat)
	rect.set_top(lat + FG_TILE_HEIGHT)
	rect.set_right(lon + get_fg_tile_span(max(abs(rect.top), abs(rect.bottom))))
	return rect

@dispatch
def get_fg_tile_bbox(ll_coords: typing.Tuple[numbers.Real, numbers.Real]):
	return get_fg_tile_bbox(ll_coords[0], ll_coords[1])

@dispatch
def get_fg_tile_bbox(tile_index: numbers.Real) -> Rectangle:
	return get_fg_tile_bbox(get_fg_tile_coords(tile_index))

@dispatch
def get_fg_tile_bbox(ll_coord: Coord) -> Rectangle:
	return get_fg_tile_bbox(ll_coord.lon, ll_coord.lat)

@dispatch
def get_fg_tile_path(lon: numbers.Real, lat: numbers.Real) -> str:
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

@dispatch
def get_fg_tile_path(coord: Coord) -> str:
	return get_fg_tile_path(coord.lon, coord.lat)

@dispatch
def get_fg_tile_path(index: int) -> str:
	return get_fg_tile_path(get_fg_tile_coords(index))

def get_fg_tile_indices(bbox: Rectangle) -> list[int]:
	bbox = Rectangle(bbox)
	bbox.set_left(fgmath.floor(bbox.left, get_fg_tile_span(max(abs(bbox.top), abs(bbox.bottom)))))
	bbox.set_right(fgmath.ceil(bbox.right, get_fg_tile_span(max(abs(bbox.top), abs(bbox.bottom)))))
	bbox.set_bottom(fgmath.floor(bbox.bottom, 0.125))
	bbox.set_top(fgmath.ceil(bbox.top, 0.125))
	
	tiles = []
	
	for lat in range(bbox.bottom, bbox.top - 0.125, 0.125):
		for lon in range(bbox.left, bbox.right - get_fg_tile_span(lat), get_fg_tile_span(lat)):
			tiles.append(get_fg_tile_index(lon, lat))
	
	return tiles

def get_fg_tile_paths(bbox: Rectangle) -> list[str]:
	bbox = Rectangle(bbox)
	bbox.set_left(fgmath.floor(bbox.left, get_fg_tile_span(max(abs(bbox.top), abs(bbox.bottom)))))
	bbox.set_right(fgmath.ceil(bbox.right, get_fg_tile_span(max(abs(bbox.top), abs(bbox.bottom)))))
	bbox.set_bottom(fgmath.floor(bbox.bottom, 0.125))
	bbox.set_top(fgmath.ceil(bbox.top, 0.125))
	
	paths = []
	for lat in range(bbox.bottom, bbox.top - 0.125, 0.125):
		for lon in range(bbox.left, bbox.right - get_fg_tile_span(lat), get_fg_tile_span(lat)):
			paths.append(get_fg_tile_path(lon, lat))
	return paths


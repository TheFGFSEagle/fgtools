#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math

from fgtools.utils import wrap_period

EARTH_RADIUS = 6378138.12

def great_circle_distance_m(lon1, lat1, lon2, lat2):
	lon1, lat1, lon2, lat2 = map(math.radians, (lon1, lat1, lon2, lat2))
	return abs(EARTH_RADIUS * math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon1 - lon2)))

def great_circle_distance_km(lon1, lat1, lon2, lat2):
	return great_circle_distance_m(lon1, lat1, lon2, lat2) / 1000

def get_bearing_deg(lon1, lat1, lon2, lat2):
	dlon = (lon2 - lon1)
	x = math.cos(math.radians(lat2)) * math.sin(math.radians(dlon))
	y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dlon))
	brg = math.atan2(x, y)
	brg = math.degrees(brg)

	return wrap_period(brg, 0, 360)

def apply_heading_distance(lon, lat, heading, distance):
	lon = math.radians(lon)
	lat = math.radians(lat)
	heading = math.radians(heading)
	distance /= EARTH_RADIUS

	if distance < 0:
		distance = abs(distance)
		heading -= math.pi

	lat = math.asin(math.sin(lat) * math.cos(distance) + math.cos(lat) * math.sin(distance) * math.cos(heading))

	if math.cos(lat) > 1e-15:
		lon = math.pi - (math.pi - lon - math.asin(math.sin(heading) * math.sin(distance) / math.cos(lat)) % (2 * math.pi))
	
	return wrap_period(math.degrees(lon), -180, 180), wrap_period(math.degrees(lat), -90, 90)
	

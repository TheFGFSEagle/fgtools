#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math

from fgtools.utils import unit_convert, wrap_period
from fgtools.geo import EARTH_RADIUS

class Coord:
	def __init__(self, lon, lat):
		self.lon = lon
		self.lat = lat
	
	def distance_m(self, other):
		lon1, lat1, lon2, lat2 = map(math.radians, (self.lon, self.lat, other.lon, other.lat))
		return abs(EARTH_RADIUS * math.acos(round(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon1 - lon2), 14)))

	def distance_km(self, other):
		return self.distance_m(other) / 1000
	
	def distance_ft(self, other):
		return unit_convert.m2ft(self.distance_m(other))
	
	def angle(self, other):
		dlon = (math.radians(other.lon) - math.radians(self.lon))
		x = math.sin(dlon) * math.cos(math.radians(other.lat))
		y = (math.cos(math.radians(self.lat)) * math.sin(math.radians(other.lat)) -
			math.sin(math.radians(self.lat)) * math.cos(math.radians(other.lat)) * math.cos(dlon))
		angle = math.degrees(math.fmod(math.atan2(x, y), 2 * math.pi))
		return wrap_period(angle, 0, 360)
	
	def apply_angle_distance_m(self, angle, distance):
		lon = math.radians(self.lon)
		lat = math.radians(self.lat)
		heading = math.radians(angle)
		distance /= EARTH_RADIUS

		if distance < 0:
			distance = abs(distance)
			heading -= math.pi

		lat = math.asin(math.sin(lat) * math.cos(distance) + math.cos(lat) * math.sin(distance) * math.cos(heading))

		if math.cos(lat) > 1e-15:
			lon = math.pi - math.fmod(math.pi - lon - math.asin(math.sin(heading) * math.sin(distance) / math.cos(lat)), (2 * math.pi))
		
		lon = math.degrees(lon)
		lat = math.degrees(lat)
		if lon > 180:
			lon -= 360
		elif lon < -180:
			lon += 360
				
		return Coord(lon, lat)


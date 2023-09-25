#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math
import typing
import numbers

from plum import dispatch
import pyproj

from fgtools.utils import unit_convert, wrap_period
from fgtools import geo

_proj_ecef = pyproj.Proj(proj='geocent', ellps='WGS84', datum='WGS84')
_proj_lla = pyproj.Proj(proj='latlong', ellps='WGS84', datum='WGS84')
_transformer_to_lla = pyproj.Transformer.from_proj(_proj_ecef, _proj_lla, always_xy=True)
_transformer_to_ecef = pyproj.Transformer.from_proj(_proj_lla, _proj_ecef, always_xy=True)

class Coord:
	@dispatch
	def __init__(self, lon: numbers.Real, lat: numbers.Real):
		self.lon = lon
		self.lat = lat
		self.alt = 0
	
	@dispatch
	def __init__(self, lon: numbers.Real, lat: numbers.Real, alt: numbers.Real):
		self.lon = lon
		self.lat = lat
		self.alt = alt
	
	@dispatch
	def __init__(self, other: typing.Tuple[numbers.Real, numbers.Real]):
		self.lon, self.lat = other
		self.alt = 0
	
	@dispatch
	def __init__(self, other: typing.Tuple[numbers.Real, numbers.Real, numbers.Real]):
		self.lon, self.lat, self.alt = other
	
	@dispatch
	def __init__(self, other: "Coord"):
		self.lon = other.lon
		self.lat = other.lat
		self.alt = other.alt
	
	@classmethod
	@dispatch
	def from_cartesian(cls, c: typing.Tuple[numbers.Real, numbers.Real, numbers.Real]):
		return Coord.from_cartesian(c[0], c[1], c[2])
	
	@classmethod
	@dispatch
	def from_cartesian(cls, x: numbers.Real, y: numbers.Real, z: numbers.Real):
		lon, lat, alt = _transformer_to_lla.transform(x, y, z, radians=False)
		return Coord(lon, lat, alt)
	
	def to_cartesian(self):
		x, y, z = _transformer_to_ecef.transform(self.lon, self.lat, self.alt, radians=False)
		return x, y, z
	
	def __repr__(self):
		return f"Coord(lon={self.lon}, lat={self.lat}, alt={self.alt})"
	
	@dispatch
	def __sub__(self, other: "Coord"):
		return Coord((self.lon - other.lon, self.lat - other.lat, self.alt))
	
	@dispatch
	def __sub__(self, other: typing.Tuple[numbers.Real, numbers.Real]):
		return Coord((self.lon - other[0], self.lat - other[1], self.alt))
	
	@dispatch
	def __isub__(self, other: "Coord"):
		self.lon -= other.lon
		self.lat -= other.lat
		return self
	
	@dispatch
	def __isub__(self, other: typing.Tuple[numbers.Real, numbers.Real]):
		self.lon -= other[0]
		self.lat -= other[1]
		return self
	
	@dispatch
	def __add__(self, other: "Coord"):
		return Coord((self.lon + other.lon, self.lat + other.lat, self.alt))
	
	@dispatch
	def __add__(self, other: typing.Tuple[numbers.Real, numbers.Real]):
		return Coord((self.lon + other[0], self.lat + other[1], self.alt))
	
	@dispatch
	def __iadd__(self, other: "Coord"):
		self.lon += other.lon
		self.lat += other.lat
		return self
	
	@dispatch
	def __iadd__(self, other: typing.Tuple[numbers.Real, numbers.Real]):
		self.lon += other[0]
		self.lat += other[1]
		return self
	
	def distance_m(self, other):
		lon1, lat1, lon2, lat2 = map(math.radians, (self.lon, self.lat, other.lon, other.lat))
		return abs(geo.EARTH_RADIUS * math.acos(round(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon1 - lon2), 14)))

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
		distance /= geo.EARTH_RADIUS

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
				
		return Coord(lon, lat, self.alt)


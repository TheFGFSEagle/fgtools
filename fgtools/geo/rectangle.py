#!/usr/bin/env python
#-*- coding:utf-8 -*-

from fgtools.geo import coord

class Rectangle:
	def __init__(self, ll, ur):
		if not (isinstance(ll, coord.Coord) and isinstance(ur, coord.Coord)):
			raise TypeError("loer left or upper right coordinate is not of type fgtools.geo.coord.Coord")
		self.ll = ll
		self.ur = ur
	
	def midpoint(self):
		return coord.Coord((self.ll.lon + self.ur.lon) / 2, (self.ll.lat + self.ur.lat) / 2)
	
	def is_inside(self, coord):
		return self.ll.lon <= coord.lon <= self.ur.lon and self.ll.lat <= coord.lat <= self.ur.lat
	
	def diagonal_m(self):
		return self.ll.distance_m(self.ur)
	
	def length_m(self):
		return self.ur.distance_m(Coord(self.ur.lon, self.ll.lat))
		
	def width_m(self):
		return self.ll.distance_m(Coord(self.ur.lon, self.ll.lat))


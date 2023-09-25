#!/usr/bin/env python
#-*- coding:utf-8 -*-

from fgtools.math import coord

class Rectangle:
	def __init__(self, ll, ur):
		if not (isinstance(ll, coord.Coord) and isinstance(ur, coord.Coord)):
			raise TypeError("loer left or upper right coordinate is not of type fgtools.math.coord.Coord")
		self.ll = ll
		self.ur = ur
	
	def midpoint(self):
		return coord.Coord((self.ll.x + self.ur.x) / 2, (self.ll.y + self.ur.y) / 2)
	
	def is_inside(self, coord):
		return self.ll.x <= coord.x <= self.ur.x and self.ll.y <= coord.y <= self.ur.y
	
	def diagonal(self):
		return self.ll.distance(self.ur)
	
	def length(self):
		return self.ur.distance(Coord(self.ur.x, self.ll.y))
		
	def width(self):
		return self.ll.distance(Coord(self.ur.x, self.ll.y))


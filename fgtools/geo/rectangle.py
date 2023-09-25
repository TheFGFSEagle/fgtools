#!/usr/bin/env python
#-*- coding:utf-8 -*-

import typing
import numbers
from plum import dispatch

from fgtools.geo.coord import Coord

class Rectangle:
	@dispatch
	def __init__(self, ll: Coord, ur: Coord):
		self.ll = ll
		self.ur = ur
		self.lr = Coord(ll.lon, ur.lat)
		self.ul = Coord(ur.lon, ll.lat)
		self.left = ll.lon
		self.top = ur.lat
		self.right = ur.lon
		self.bottom = ll.lat
	
	@dispatch
	def __init__(self, ll: typing.Iterable[typing.Union[int, float]], ur: typing.Iterable[typing.Union[int, float]]):
		self.ll = Coord(ll[0], ll[1])
		self.ur = Coord(ur[0], ur[1])
		self.lr = Coord(self.ll.lon, self.ur.lat)
		self.ul = Coord(self.ur.lon, self.ll.lat)
		self.left = self.ll.lon
		self.top = self.ur.lat
		self.right = self.ur.lon
		self.bottom = self.ll.lat
	
	@dispatch
	def __init__(self, coords: typing.Iterable[numbers.Real]):
		self.ll = Coord(coords[0], coords[1])
		self.ur = Coord(coods[2], coords[3])
		self.lr = Coord(self.ll.lon, self.ur.lat)
		self.ul = Coord(self.ur.lon, self.ll.lat)
		self.left = self.ll.lon
		self.top = self.ur.lat
		self.right = self.ur.lon
		self.bottom = self.ll.lat
	
	@dispatch
	def __init__(self, left: numbers.Real, bottom: numbers.Real, right: numbers.Real, top: numbers.Real):
		self.ll = Coord(left, bottom)
		self.ur = Coord(right, top)
		self.lr = Coord(self.ll.lon, self.ur.lat)
		self.ul = Coord(self.ur.lon, self.ll.lat)
		self.left = self.ll.lon
		self.top = self.ur.lat
		self.right = self.ur.lon
		self.bottom = self.ll.lat
	
	@dispatch
	def __init__(self, other: "Rectangle"):
		self.ll = Coord(other.ll.lon, other.ll.lat)
		self.ur = Coord(other.ur.lon, other.ur.lat)
		self.lr = Coord(other.lr.lon, other.lr.lat)
		self.ul = Coord(other.ul.lon, other.ul.lat)
		self.left = other.left
		self.top = other.top
		self.right = other.right
		self.bottom = other.bottom
	
	def __iter__(self):
		return iter([self.ll, self.ul, self.ur, self.ul])
	
	def __repr__(self):
		return f"Rectangle(left={self.left}, top={self.top}, right={self.right}, bottom={self.bottom})"
	
	def set_left(self, left: float):
		self.left = left
		self.ll.lon = left
		self.ul.lon = left
	
	def set_right(self, right: float):
		self.right = right
		self.lr.lon = right
		self.ur.lon = right
	
	def set_top(self, top: float):
		self.top = top
		self.ul.lat = top
		self.ur.lat = top
	
	def set_bottom(self, bottom: float):
		self.bottom = bottom
		self.ll.lat = bottom
		self.lr.lat = bottom
	
	def midpoint(self):
		return Coord((self.ll.lon + self.ur.lon) / 2, (self.ll.lat + self.ur.lat) / 2)
	
	def is_inside(self, coord):
		return self.ll.lon <= coord.lon <= self.ur.lon and self.ll.lat <= coord.lat <= self.ur.lat
	
	def diagonal_m(self):
		return self.ll.distance_m(self.ur)
	
	def length_m(self):
		return self.ur.distance_m(Coord(self.ur.lon, self.ll.lat))
		
	def width_m(self):
		return self.ll.distance_m(Coord(self.ur.lon, self.ll.lat))


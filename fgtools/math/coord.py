#!/usr/bin/env python
#-*- coding:utf-8 -*-

class Coord:
	def __init__(self, x, y):
		self.x = x
		self.y = y
	
	def distance(self, other):
		return math.sqrt((other.x - self.x) ** 2 + (other.y - self.y) ** 2)
	
	def angle(self, other):
		return math.degrees(math.atan2(other.x - self.x, other.y - self.y))
	
	def apply_angle_distance(self, angle, distance):
		angle_rad = math.pi / 2 - math.radians(angle)
		return Coord(self.x + distance * math.cos(angle_rad), self.y + distance * math.sin(angle_rad))

#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math

class Interpolator:
	def __init__(self):
		self._indexes = []
		self._values = []
		self._sorted = False
	
	def add_value(self, index, value):
		if type(index) not in (int, float) or type(value) not in (int, float):
			try:
				index = float(index)
				value = float(value)
			except ValueError:
				raise TypeError(f"Interpolator.add_value: index '{index}' or value '{value}' not a number")
		
		self._indexes.append(index)
		self._values.append(value)
		self._sorted = False
	
	def add_values(self, indexes, values):
		for i, v in zip(indexes, values):
			self.add_value(i, v)
	
	def interpolate(self, index, extrapolate=True, method="linear", sort=True):
		if not hasattr(self, "_interpolate_" + method):
			raise NotImplementedError(f"Interpolator.interpolate: interpolation method '{method}' not yet supported")
		
		if len(self._indexes) < 2:
			raise ValueError(f"Interpolator.interpolate: cannot interpolate on a table with less than two data points")
		
		# only sort if not already sorted to increase performance for large tables
		if sort and not self._sorted:
			items = sorted(list(zip(self._indexes, self._values)), key=lambda t: t[0])
			self._indexes = []
			self._values = []
			for item in items:
				self._indexes.append(item[0])
				self._values.append(item[1])
			self._sorted = True
		
		if index in self._indexes:
			return self._values[self._indexes.index(index)]
		
		if self._indexes[0] < index < self._indexes[-1]:
			return getattr(self, "_interpolate_" + method)(index, extrapolate)
		else:
			if not extrapolate:
				if index < self._indexes[0]:
					return self._values[0]
				else:
					return self._values[-1]
			else:
				if index < self._indexes[0]:
					return self._values[1] + (index - self._indexes[1]) / (self._indexes[0] - self._indexes[1]) * (self._values[0] - self._values[1])
				else:
					return self._values[-2] + (index - self._indexes[-2]) / (self._indexes[-1] - self._indexes[-2]) * (self._values[-1] - self._values[-2])
	
	def _find_neighbours(self, index):
		lower = upper = 0
		last = self._indexes[0]
		for it, _index in enumerate(self._indexes):
			lower = last
			last = it
			if _index > index:
				upper = it
				break
		
		return lower, upper
	
	def _interpolate_linear(self, index, extrapolate=True):
		lower, upper = self._find_neighbours(index)
		return self._values[lower] + (self._values[upper] - self._values[lower]) * (index - self._indexes[lower]) / (self._indexes[upper] - self._indexes[lower])
	
	def _interpolate_sinusoidal(self, index, extrapolate=True):
		lower, upper = self._find_neighbours(index)
		return self._values[lower] + (self._values[upper] - self._values[lower]) * math.sin(math.radians((index - self._indexes[lower]) / (self._indexes[upper] - self._indexes[lower]) * 90))

# run test if run directly
if __name__ == "__main__":
	print("Test results:")
	print()
	i = Interpolator()
	i.add_values((0, 10, 20), (0, 20, 30))
	test_vals = (-5, 0, 1, 2, 3.5, 5.55555, 10, 15, 35, 100)
	
	for method in ("linear", "sinusoidal"):
		print(method.capitalize() + ":")
		for test_val in test_vals:
			print(test_val, "=>", i.interpolate(test_val, method=method))
		print()


#!/usr/bin/env python
#-*- coding:utf-8 -*-

class Interpolator:
	def __init__(self):
		self._indexes = []
		self._values = []
		self._sorted = False
		
		self.methods = {"linear": self._interpolate_linear}
	
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
		if not method in self.methods:
			raise NotImplementedError(f"Interpolator.interpolate: interpolation method '{method}' not yet supported")
		
		if len(self._indexes) < 2:
			raise ValueError(f"Interpolator.interpolate: cannot interpolate on a table with less than two data points")
		
		# only sort if not already sorted to increase performance for large tables
		if not self._sorted and sort:
			self._indexes.sort()
			self._values.sort()
			self._sorted = True
		
		return self.methods[method](index, extrapolate)
	
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
		if index in self._indexes:
			return self._values[self._indexes.index(index)]
		
		if self._indexes[0] < index < self._indexes[-1]:
			lower, upper = self._find_neighbours(index)
			return self._values[lower] + (self._values[upper] - self._values[lower]) * (index - self._indexes[lower]) / (self._indexes[upper] - self._indexes[lower]) 
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

# run test if run directly
if __name__ == "__main__":
	print("Test results")
	i = Interpolator()
	i.add_values((0, 10, 20), (0, 20, 30))
	for test_val in (-5, 0, 1, 2, 3.5, 5.55555, 9, 10, 15, 100):
		print(test_val, i.interpolate(test_val))
	


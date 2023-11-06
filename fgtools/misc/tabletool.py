#!/usr/bin/env python
#-*- coding:utf-8 -*-

import argparse

class TableRow:
	def __init__(self, cols):
		self.values = [None] * cols
	
	def __len__(self):
		return len(self.values)
	
	def __setitem__(self, index, value):
		if index >= len(self.values):
			raise IndexError(f"column index {index} out of bounds for row with {len(self.values)} columns")
		self.values[index] = value
	
	def __getitem__(self, index):
		if index >= len(self.values):
			raise IndexError(f"column index {index} out of bounds for row with {len(self.values)} columns")
		return self.values[index]
	
	def __imul__(self, other):
		if len(self.values) != len(other.values):
			raise IndexError(f"attempting to perform *= on two table rows with different column counts")
		for i in range(len(self)):
			self[i] *= other[i]
		return self
	
	def __isub__(self, other):
		if len(self.values) != len(other.values):
			raise IndexError(f"attempting to perform -= on two table rows with different column counts")
		for i in range(len(self)):
			self[i] -= other[i]
		return self
	
	def __iadd__(self, other):
		if len(self.values) != len(other.values):
			raise IndexError(f"attempting to perform += on two table rows with different column counts")
		for i in range(len(self)):
			self[i] += other[i]
		return self

class Table:
	def __init__(self, rows, cols):
		self.rows = [TableRow(cols) for i in range(rows)]
	
	def __getitem__(self, index):
		if index >= len(self.rows):
			raise IndexError(f"row index {index} out of bounds for table with {len(self.rows)} rows")
		return self.rows[index]
	
	def __imul__(self, other):
		if len(self.rows) != len(other.rows):
			raise IndexError(f"attempting to perform *= on two tables of different row count")
		for selfrow, otherrow in zip(self, other):
			selfrow *= otherrow
		return self
	
	def __isub__(self, other):
		if len(self.rows) != len(other.rows):
			raise IndexError(f"attempting to perform -= on two tables of different row count")
		for selfrow, otherrow in zip(self, other):
			selfrow -= otherrow
		return self
	
	def __iadd__(self, other):
		if len(self.rows) != len(other.rows):
			raise IndexError(f"attempting to perform += on two tables of different row count")
		for selfrow, otherrow in zip(self, other):
			selfrow += otherrow
		return self

def add_table(tables):
	lines = []
	EOT = False
	EOF = False
	while not EOT and not EOF:
		line = input().strip()
		if line.lower() == "eot":
			EOT = True
		elif line.lower() == "eof":
			EOF = True
		else:
			lines.append(list(filter(None, line.split())))
	
	if len(lines) > 0:
		tables.append(lines)
	
	return EOF

def parse_tables(tables):
	newtables = []
	for table in tables:
		t = Table(len(table), max(map(len, table)))
		for i, row in enumerate(table):
			for j, col in enumerate(table[i]):
				t[i][j] = float(table[i][j])
		newtables.append(t)
	return newtables

def perform_operation(tables, op):
	first, *tables = tables
	for table in tables:
		if op == "product":
			first *= table
		elif op == "difference":
			first -= table
		elif op == "sum":
			first += table
	return first

def print_table(table, precision):
	for row in table:
		print("\t".join(map(lambda f: str(round(f, precision)), row)))
	
def main():
	argp = argparse.ArgumentParser(description="perform various operations on one or more tables")
	
	argp.add_argument(
		"-o", "--operation",
		help="which operation to perform on the inputted tables",
		required=True,
		choices=["product", "difference", "sum"]
	)
	
	argp.add_argument(
		"-p", "--precision",
		help="Number of decimal places the numbers in the outputted table should have",
		default=6,
		type=int
	)
	
	args = argp.parse_args()
	
	print("Input as many tables as you want, but at least two - input 'EOF' (without the quotes) when you are done")
	print("For each table, input as many table rows as you want - input 'EOT' (without the quotes) to end a table")
	print("For each table row, the columns can be separated by any amount of tabs or spaces")
	tables = []
	EOF = False
	while not EOF:
		EOF = add_table(tables)
	tables = parse_tables(tables)
	table = perform_operation(tables, args.operation)
	print_table(table, args.precision)

if __name__ == '__main__':
	main()




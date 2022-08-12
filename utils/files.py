#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os

from fgtools.utils import isiterable

def find_input_files(paths, prefix="", suffix=""):
	if not isiterable(paths):
		if isinstance(paths, str):
			paths = [paths]
		else:
			raise TypeError("paths is not iterable")
	
	files = []
	for path in paths:
		if os.path.isfile(path) and os.path.split(path)[-1].startswith(prefix) and path.endswith(suffix):
			files.append(path)
		elif os.path.isdir(path):
			files += find_input_files([os.path.join(path, s) for s in os.listdir(path)])
		else:
			print(f"Input file / directory {path} does not exist - skipping")
	
	return files

def write_xml_header(f):
	f.write('<?xml version="1.0" encoding="UTF-8"?>\n')


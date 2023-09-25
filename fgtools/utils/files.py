#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import logging
import requests
import datetime
import dateutil.parser

from fgtools.utils import isiterable, download
from fgtools.utils.constants import CACHEDIR

def find_input_files(paths, prefix="", suffix=""):
	if not isiterable(paths):
		if isinstance(paths, str):
			paths = [paths]
		else:
			raise TypeError("paths is not iterable / not a string")
	
	files = []
	for path in paths:
		if os.path.isfile(path):
			if os.path.split(path)[-1].startswith(prefix) and path.endswith(suffix):
				files.append(path)
		elif os.path.isdir(path):
			files += find_input_files([os.path.join(path, s) for s in os.listdir(path)], prefix, suffix)
		else:
			print(f"Input file / directory {path} does not exist - skipping")
	
	return files

def write_xml_header(f):
	f.write('<?xml version="1.0" encoding="UTF-8"?>\n')

def check_exists(path, exit=True, type="file", create=True):
	if type not in ("file", "dir"):
		raise ValueError(f'check_exists() got an unrecognized value {type} for argument "type" - must be either "file" or "dir" !')
	
	if not path:
		raise ValueError(f'check_exists() got an empty path !')
	
	action = ("skipping", "exiting")[exit]
	# logging.fatal returns nothing so this will always succeed
	func = (logging.warn, lambda s: logging.fatal(s) or sys.exit(1))[exit]
	if os.path.isfile(path):
		if type == "file":
			return 1
		else:
			func(f"Path {path} is not a file - {action} !")
			return 2
	elif os.path.isdir(path):
		if type == "dir":
			return 1
		else:
			func(f"Path {path} is not a directory - {action} !")
			return 2
	else:
		if create:
			logging.info(f"Creating non-existent path {path}")
			if type == "file":
				parts = os.path.split(path)
				if len(parts) > 1:
					os.makedirs(os.path.join(*parts[:-1]), exist_ok=True)
				else:
					os.makedirs(".", exist_ok=True)
				with open(path, "a") as f:
					pass
			else:
				os.makedirs(path, exist_ok=True)
			return 3
		else:
			func(f"Path {path} does not exist - {action} !")
			return 0

def get_cached_file(url, path=None, progress=True, prolog="Downloading '{path}' - ", blocksize=1000):
	path = path or os.path.join(CACHEDIR, url.replace("/", "_"))
	download(url, path, progress=progress, prolog=prolog, blocksize=blocksize)
	return path

def get_newest_mtime(paths, prefix="", suffix=""):
	if not isiterable(paths):
		if isinstance(paths, str):
			paths = [paths]
		else:
			raise TypeError("paths is not iterable / not a string")
	paths = list(filter(os.path.exists, paths))
	files = find_input_files(paths, prefix, suffix)
	if not files:
		return 99999999999999999999999999999999999999999999999999999999999
	return max(map(os.path.getmtime, files))


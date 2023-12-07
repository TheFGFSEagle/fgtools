#!/usr/bin/env python
#-*- coding:utf-8 -*-

import math
import os
import sys
import subprocess
import time
import requests
import shutil

import datetime
from dateutil.parser import parse as parsedate

import tqdm

from fgtools import get_logger

def make_fgelev_pipe(fgelev, fgscenery, fgdata):
	print("Creating pipe to fgelev … ", end="")
	sys.stdout.flush()
	env = os.environ.copy()
	env["FG_SCENERY"] = os.pathsep.join(fgscenery)
	env["FG_ROOT"] = fgdata
	pipe = subprocess.Popen(args=[fgelev, "--expire", "1"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	pipe.stdout.flush()
	pipe.stdout.readline()
	pipe.stdin.flush()
	pipe.stdin.flush()
	print("done")
	return pipe

def isiterable(o, striterable=False):
	if isinstance(o, str):
		return striterable
	else:
		if hasattr(o, "__iter__"):
			return True
		else:
			return False

def wrap_period(n, min, max):
	while n > max:
		n -= max - min
	
	while n < min:
		n += max - min
	
	return n

def range(stop, start=None, step=1):
	if start:
		stop, start = start, stop
	else:
		start = 0
	yield round(start, 14)
	i = 0
	r = start
	while r < stop:
		i += 1
		r = start + i * step
		yield round(r, 14)

def format_size(size, decimal_places=1):
	for unit in ["", "K", "M", "G", "T", "P"]:
		if size < 1000 or unit == 'P':
			break
		size /= 1000
	return f"{size:.{decimal_places}f} {unit}B"

def download(url, path, progress=True, prolog="Downloading '{path}'", blocksize=1000, force=False, update=True):
	with requests.get(url, stream=True) as remote:
		if remote.status_code >= 400:
			get_logger().error(f"Request to {url} failed with status code {remote.status_code}")
			return False
		
		content_length = int(remote.headers["Content-Length"])
		
		if os.path.exists(path):
			url_time = parsedate(remote.headers['last-modified']).replace(tzinfo=None)
			file_time = datetime.datetime.fromtimestamp(os.path.getmtime(path)).replace(tzinfo=None)
			
			if (url_time <= file_time or not update) and content_length == os.stat(path).st_size and not force:
				return True

		with open(path, "wb") as local:
			pbar = tqdm.tqdm(desc=prolog.format(path=path), total=content_length, unit="B", unit_scale=True)
			for chunk in remote.iter_content(chunk_size=blocksize):
				local.write(chunk)
				pbar.update(len(chunk))
	return True

def padded_print(s, pad_str=" ", end=None):
	print(s + pad_str * (shutil.get_terminal_size()[0] - len(s)), end=end)

def read_timestamp(path):
	timestamp_path = path + ".timestamp"
	if not os.path.exists(timestamp_path):
		return -1
	
	with open(timestamp_path, "r") as timestamp_file:
		try:
			return float(timestamp_file.read().strip())
		except ValueError:
			return -1

def write_timestamp(path):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	timestamp_path = path + ".timestamp"
	with open(timestamp_path, "w") as timestamp_file:
		timestamp_file.write(str(time.time()))

def run_command(cmd, error_log_path=None):
	error_log_path = (error_log_path or cmd.replace("/", "_")) + ".log"
	get_logger().debug(f"Running command: {cmd}")
	p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
	if p.returncode != 0:
		os.makedirs(os.path.dirname(error_log_path) or ".", exist_ok=True)
		with open(error_log_path, "wb") as log_file:
			log_file.write(cmd.encode("utf-8") + b"\n\n")
			log_file.write(p.stdout)
		get_logger().fatal(f"\nCommand '{cmd}' exited with return code {p.returncode} - see {error_log_path} for details.")
	return p.returncode

def quote(s, quote="\"", n=1):
	return (quote * n) + str(s) + (quote * n)


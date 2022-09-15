#!/usr/bin/env python
#-*- coding:utf-8 -*-

import subprocess

class Pipe:
	def __init__(self, fgelev, fgscenery, fgdata):
		print("Creating pipe to fgelev … ", end="")
		sys.stdout.flush()
		self.env = os.environ.copy()
		self.env["FG_SCENERY"] = os.pathsep.join(fgscenery)
		self.env["FG_ROOT"] = fgdata
		self.pipe = subprocess.Popen(args=[fgelev, "--expire", "1"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		self.pipe.stdout.flush()
		self.pipe.stdout.readline()
		self.pipe.stdin.flush()
		self.pipe.stdin.flush()
		print("done")
	
	def get_elevation(self, lon, lat):
		elevpipe.stdin.write(f"_ {lon} {lat}\n".encode("utf-8"))
		elevpipe.stdin.flush()
		elevout = elevpipe.stdout.readline().split()
		if len(elevout) == 2:
			return float(elevout[1])
		else
	

#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import argparse
import random
import sys

from fgtools.dsf2stg_lookup import lookup
from fgtools import utils
from fgtools.utils.files import find_input_files

cars = [
	"hatchback_red.ac",
	"hatchback_blue.ac",
	"hatchback_black.ac",
	"hatchback_black.ac",
	"hatchback_silver.ac",
	"hatchback_silver.ac",
	"hatchback_green.ac",
	"van_blue_dirty.ac",
	"van_red.ac",
	"van_silver.ac"
] 

cessnas = [
	"Cessna172.ac",
	"Cessna172_blue.ac",
	"Cessna172_green.ac",
	"Cessna172_red.ac",
	"Cessna172_sky.ac",
	"Cessna172_yellow.ac",
	"Cessna150_no_reg.ac"
]

def parse_txt_file(path):
	with open(path) as f:
		content = list(map(str.strip, f.readlines()))
	
	objpaths = []
	for line in content:
		if line.startswith("OBJECT_DEF"):
			objpaths.append(line.split()[1])
	
	objects = []
	for line in content:
		if line.startswith("OBJECT "):
			line = line.split()
			objects.append({"path": objpaths[int(line[1])], "lon": float(line[2]), "lat": float(line[3]), "hdg": float(line[4])})
	
	return objects

def parse_txt_files(files):
	objects = []
	total = len(files)
	i = 1
	for f in files:
		print(f"\rParsing DSF/TXT files …  {i / total * 100:.1f}% ({i} of {total})", end="")
		sys.stdout.flush()
		objects += parse_txt_file(f)
		i += 1
	print()
	return objects

def calc_object_elevs(objects, fgelev_pipe):
	total = len(objects)
	i = 1
	for o in objects:
		print(f"\rCalculating object elevations … {i / total * 100:.1f}% ({i} of {total})", end="")
		sys.stdout.flush()
		fgelev_pipe.stdin.write(f"{o['path']} {o['lon']} {o['lat']}\n".encode("utf-8"))
		fgelev_pipe.stdin.flush()
		fgelevout = fgelev_pipe.stdout.readline().split()
		if len(fgelevout) == 2:
			o["alt"] = float(fgelevout[1])
		else:
			print(f"\rReceived unusable output from FGElev: {fgelevout} for longitude {o['lon']} and latitude {o['lat']} - skipping object")
			print(f"\rCalculating object elevations … {i / total * 100:.1f}% ({i} of {total})", end="")
		i += 1
	print()
	return objects

def group_objects_by_tile(objects):
	tiles = {}
	for o in objects:
		tile_index = utils.get_fg_tile_index(o["lon"], o["lat"])
		if not tile_index in tiles:
			tiles[tile_index] = []
		tiles[tile_index].append(o)
	
	return tiles

def write_stg_files(objects, output):
	total = len(objects)
	i = 1
	not_found_xpaths = []
	for tile_index in objects:
		print(f"\rWriting STG files … {i / total * 100:.1f}% ({i} of {total})", end="")
		sys.stdout.flush()
		stgpath = os.path.join(output, utils.get_fg_tile_path(objects[tile_index][0]["lon"], objects[tile_index][0]["lat"]) + ".stg")
		os.makedirs(os.path.join(*os.path.split(stgpath)[:-1]), exist_ok=True)
		with open(stgpath, "w") as f:
			for o in objects[tile_index]:
				opath = lookup.get(o["path"], None)
				if not opath:
					if o["path"] not in not_found_xpaths:
						print(f"\rNo FlightGear model found for XPlane model {o['path']} - skipping")
						print(f"\rWriting STG files … {i / total * 100:.1f}% ({i} of {total})", end="")
						not_found_xpaths.append(o["path"])
					continue
				
				opath = opath["path"]
				
				if opath == "CAR":
					opath = "Models/Transport/" + random.choice(cars)
				elif opath == "CESSNA":
					opath = "Models/Aircraft/" + random.choice(cessnas)
				
				f.write(f"OBJECT_SHARED {opath} {o['lon']} {o['lat']} {o['alt'] + lookup[o['path']]['alt-offset']} {o['hdg'] + lookup[o['path']]['hdg-offset']}\n")
		i += 1	
	print()

def main():
	argp = argparse.ArgumentParser(description="Convert XPlane scenery DSF/TXT files to FlightGear scenery STG files")
	
	argp.add_argument(
		"-i", "--input",
		help="Input DSF/TXT file or directory containing such files",
		required=True,
		nargs="+"
	)
	
	argp.add_argument(
		"-o", "--output",
		help="Output directory to put produced STG files into",
		required=True
	)
	
	argp.add_argument(
		"-s", "--fgscenery",
		help="Path to FlightGear scenery directories containing Terrain, more than one directory can be passed.",
		nargs="+",
		default=["~/TerraSync", "~/TerraSync/TerraSync", "TerraSync", "TerraSync/TerraSync"]
	)
	
	argp.add_argument(
		"-d", "--fgdata",
		help="Path to FlightGear data directory.",
		default="~/fgdata"
	)
	
	argp.add_argument(
		"-e", "--fgelev",
		help="Name of / path to fgelev executable",
		default="fgelev",
	)
	
	args = argp.parse_args()
	
	print("Searching for DSF/TXT files … ", end="")
	sys.stdout.flush()
	txt_files = find_input_files(args.input)
	print(f"done, found {len(txt_files)} files")
	
	objects = parse_txt_files(txt_files)
	print("Connecting to fgelev … ", end="")
	sys.stdout.flush()
	fgelev_pipe = utils.make_fgelev_pipe(args.fgelev, args.fgscenery, args.fgdata)
	print("done")
	elev_objects = calc_object_elevs(objects, fgelev_pipe)
	print("Grouping objects by tile … ", end="")
	sys.stdout.flush()
	stg_groups = group_objects_by_tile(elev_objects)
	print("done")
	write_stg_files(stg_groups, args.output)

if __name__ == '__main__':
	main()



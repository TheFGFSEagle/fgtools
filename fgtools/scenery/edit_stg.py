#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import argparse
import sys
import os
import subprocess
import time

from fgtools.utils import make_fgelev_pipe
from fgtools.utils import files

class SkipReason:
	NotFound = 0
	DirEmpty = 1
	NoSTG = 2

def read_stg_file(path):
	result = []
	offset = 0
	skipnext = False
	with open(path, "r") as fp:
		content = fp.readlines()
		for number, line in enumerate(content):
			line = line.strip()
			if line.startswith("#"): # is a comment
				if line.startswith("# offset"):
					offset = line.split(" ")[-1]
					result.append(line)
				elif line.startswith("# skipnext"):
					skipnext = True
					result.append(line)
				else:
					offset = 0
					skipnext = False
					result.append(line)
			elif line.strip() == "": # empty line
				result.append(line)
			else: # is an object
				etype, *data = list(map(lambda s: s.strip(), line.split(" ")))
				if etype in ["OBJECT_SHARED", "OBJECT_SHARED_AGL", "OBJECT_STATIC", "OBJECT_STATIC_AGL", "OBJECT_SIGN", "OBJECT_SIGN_AGL", "BUILDING_ROUGH", "BUILDING_DETAILED", "OBJECT_ROAD_ROUGH", "OBJECT_ROAD_DETAILED", "OBJECT_RAILWAY_ROUGH", "OBJECT_RAILWAY_DETAILED", "OBJECT_BUILDING_MESH_ROUGH", "OBJECT_BUILDING_MESH_DETAILED"]:
					if len(data) == 5:
						objectfile, longitude, latitude, elevation, heading, pitch, roll = *data, 0, 0
					elif len(data) == 7:
						objectfile, longitude, latitude, elevation, heading, pitch, roll = data
					else:
						print(f"Warning: file {path}, line {number} is malformed - not recalculating elevation")
						result.append(line)
						continue
					
					result.append({
						"etype": etype,
						"objectfile": objectfile,
						"longitude": longitude,
						"latitude": latitude,
						"elevation": float(elevation),
						"offset": float(offset),
						"heading": heading,
						"pitch": pitch,
						"roll": roll,
						"skip": skipnext
					})
				elif etype in ["BUILDING_LIST", "TREE_LIST"]:
					if len(data) == 5:
						objectfile, material, longitude, latitude, elevation = data
					else:
						print(f"Warning: file {path}, line {number} is malformed - not recalculating elevation")
						result.append(line)
						continue
					result.append({
						"etype": etype,
						"objectfile": objectfile,
						"material": material,
						"longitude": longitude,
						"latitude": latitude,
						"elevation": float(elevation),
						"offset": float(offset),
						"skip": skipnext
					})
				elif etype in ["OBJECT", "OBJECT_BASE",  "LINEAR_FEATURE_LIST"]:
					result.append(line)
				else:
					print(f"Warning: file {path} line {number} has wrong type - commenting out to prevent FG not loading scenery")
					result.append("# " + line)
	return result

def read_stg_files(paths):
	stg_dict = dict.fromkeys(paths, {"infiles": [], "contents": []})
	for path in paths:
		if not os.path.exists(path):
			print(f"Warning: Input file / directory {path} does not exist, skipping")
			stg_dict[path] = SkipReason.NotFound
		elif os.path.isdir(path):
			for file in os.listdir(path):
				if os.splitext(path)[1] == ".stg":
					realpath = os.path.join(path, file)
					content = read_stg_file(realpath)
					stg_dict[path]["infiles"].append(file)
					stg_dict[path]["contents"].append(content)
			else:
				print(f"Warning: No STG file found in input directory {path}, skipping")
				stg_dict[path] = SkipReason.DirEmpty
		else:
			if os.path.splitext(path)[1] == ".stg":
				content = read_stg_file(path)
				stg_dict[path]["infiles"].append(path)
				stg_dict[path]["contents"].append(content)
			else:
				print(f"Warning: Input file {path} is not an STG file, skipping")
				stg_dict[path] = SkipReason.NoSTG
	return stg_dict

def recalc_elevs(stg_dict, elevpipe):
	for path in stg_dict:
		if type(stg_dict[path]) == int: # some SkipReason, so let's skip this path
			continue
		else:
			for content in stg_dict[path]["contents"]:
				for object in content:
					if type(object) == str:
						continue
					elif type(object) == dict:
						if "elevation" in object.keys():
							if not object["skip"]:
								print(f"Recalculating elevation of {object['objectfile']}")
								elevpipe.stdin.write(f"{object['objectfile']} {object['longitude']} {object['latitude']}\n".encode("utf-8"))
								elevpipe.stdin.flush()
								fgelevout = elevpipe.stdout.readline().split()
								if len(fgelevout) == 2:
									object["elevation"] = float(fgelevout[1])
							else:
								print(f"Skipping {object['objectfile']}")
							object["elevation"] += object["offset"]
							print(f"Final elevation: {object['elevation']} meters, offset was {object['offset']}")
	return stg_dict

def write_stg_files(output_stg, outfiles):
	for i, path in enumerate(output_stg):
		for infile, content in zip(output_stg[path]["infiles"], output_stg[path]["contents"]):
			if len(outfiles) == 1:
				if outfiles[0] == "__INPUT__":
					outfile = infile
				else:
					outfile = outfiles[0]
			else:
				if i < len(outfiles):
					outfile = outfiles[i]
				else:
					outfile = outfiles[-1]
			
			with open(outfile, "w") as outfp:
				for object in content:
					if type(object) == str:
						line = object
					else:
						if object["etype"] in ["BUILDING_LIST", "TREE_LIST"]:
							line = f"{object['etype']} {object['objectfile']} {object['material']} {object['longitude']} {object['latitude']} {object['elevation']}"
						else:
							line = f"{object['etype']} {object['objectfile']} {object['longitude']} {object['latitude']} {object['elevation']} {object['heading']}"
							if "pitch" in object.keys():
								line += f" {object['pitch']} {object['roll']}"
					line += "\n"
					outfp.write(line)
	return 0

def main():
	argp = argparse.ArgumentParser(description="Perform various STG file operations such as recalculating the elevation of models")
	
	argp.add_argument(
		"-i", "--input",
		help="Input STG file / folder containing such files. Mandatory, more than one file / directory can be passed",
		nargs="+",
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
		help="Path to FGelev",
		default="fgelev",
	)
	
	argp.add_argument(
		"-o", "--output",
		help="Output STG file. Default is to overwrite the input file(s).",
		nargs="+",
		default=["__INPUT__"]
	)
	
	args = argp.parse_args()
	infiles = files.find_input_files(args.input)
	outfiles = args.output
	fgdata = args.fgdata
	fgscenery = args.fgscenery
	fgelev = args.fgelev
	
	elevpipe = make_fgelev_pipe(fgelev, fgscenery, fgdata)
	input_stg = read_stg_files(infiles)
	output_stg = recalc_elevs(input_stg, elevpipe)
	exitstatus = write_stg_files(output_stg, outfiles)
	return exitstatus

if __name__ == "__main__":
	sys.exit(main())

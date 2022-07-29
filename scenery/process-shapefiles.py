#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Script that merges, slices, and decodes OSM shapefiles as needed by parsing the coordinates input and the extent of all shapefiles.

import os
import sys
import glob
import re
import argparse
import subprocess

DESCRIPTION = """
process-shapefiles.py - merges, slices, and decodes OSM shapefiles

IMPORTANT: CORINE shapefiles are NOT YET SUPPORTED !!!

This script recursively searches the specified input directory for files containing 'osm' and ending with '.shp'.
All that are found are then categorized into multiple categories - one for landuse, one for landmass, one for roads, etc.
For this reason, you may only remove the 'gis_' and '_free_1' parts from the shapefile's names !
Everything else in the name must be conserved in order for your resulting scenery not to have big areas of default landmass terrain !''

Then, for each shapefile in each category the extents will be queried using ogrinfo. To reduce processing time on subsequent runs, the results will be cached.
Then, the script will decide whether to merge or slice the shapefiles for each category based on the coordinates you input.
It will merge / slice the files accordingly with ogr2ogr.
As the final step, the resulting shapefiles will be decoded into files that tg-constrcut can read using ogr-decode.
"""

def find(src):
	osm_shapefiles = []
	shapefiles = glob.glob(os.path.join(src, "**", "**.shp")
	for file in files:
		if "osm" in os.path.split(file):
			osm_shapefiles.append(file)
	return sorted(osm_shapefiles)

def categorize(shapefiles):
	catnames = ["buildings", "landuse", "natural", "places", "pofw", "pois", "railways", "roads", "traffic", "transport", "water", "waterways"]
	categorized = []
	
	for shapefile in shapefiles:
		name = os.path.split(shapefile)[-1].split(".")[0]
		
		# Skip if the name is of the form gis_osm_landuse_a_free_1
		# these files are much smaller than the ones without _a_, probably contain less data.
		if "_a_" in name: 
			continue
		
		name = re.sub(r"gis|osm|a|free|_|(1-9)", "", name) # gis_osm_landuse_a_free_1 becomes just landuse
		# Skip if the name is not a recognized catname
		if not name in catnames:
			continue
		
		categorized.append({"path": shapefile, "category": name})
	return categorized

def get_extents(categorized):
	for shapefile in categorized:
		cmd = f"ogrinfo -al -so -ro -nocount -nomd {shapefile['path']}"
		query = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		output = list(map(lambda s: s.decode(), query.stdout.splitlines())) # subprocess.Popen.stdout is a binary file - we need normal strings
		
		extents = [s for s in output  if "Extent" in s]
		feature_count = [s for s in output  if "Feature Count" in s]
		
		if len(extents) != 1 or len(feature_count) != 1:
			print("ERROR: Fetching shapefile information using ogrinfo failed.")
			print("               Try reinstalling it through your package manager.")
			print("               If that doesn't help, please file a bug report at <github.com/TheFGFSEagle/terragear-tools/issues>.")
			print("               If you do that, please attach the process-shapefiles-bugreport.md file in order for the maintainers to be able to help you.")
			
			with open("process-shapefile-bugreport.md", "w") as f:
				f.write(f"### Output of `{cmd}`")
				f.writelines(output)
				f.write(f"### ogrinfo version:")
				f.write(subprocess.run("ogrinfo --version", stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True).stdout.deocde())
			sys.exit(2)
		
		# convert "Extent: (10.544425, 51.500000) - (11.500000, 52.500000)" to {"xll": 10.544425, "yll": 51.5, "xur": 11.5, "yur": 52,5]
		extents = dict(zip(["xll", "yll", "yur", "yur"], map(float, re.sub(r"Extent:\s\(|\)", "", extents[0]).replace(") - (", ", ").split(", "))))
		shapefile["extents"] = extents
		

def merge_slice(shapefiles, coords):
	pass

def decode(shapefiles, dest):
	pass

if __name__ == "__main__":
	argp = argparse.ArgumentParser(description="process-shapefiles.py - merges, slices, and decodes OSM shapefiles")
	
	argp.add_argument(
		"-v", "--version",
		action="version",
		version=f"TerraGear tools {'.'.join(map(str, constants.__version__))}"
	)
	
	argp.add_argument(
		"-d", "--description",
		help="display an extended description of what this script does and exit"
	)
	
	argp.add_argument(
		"-i", "--input-folder",
		help="folder containing folder 'shapefiles_raw' containing folders containing unprocessed shapefiles(default: %(default)s)",
		default="./data",
		metavar="FOLDER"
	)

	argp.add_argument(
		"-o", "--output-folder",
		help="folder to put ogr-decode result into (default: %(default)s)",
		default="./work",
		metavar="FOLDER"
	)
	
	argp.add_argument(
		"-c", "--cache-folder",
		help="where to put cache folder (default: %(default)s)",
		default=os.path.join(constants.HOME, ".cache", "tgtools")
	)
	
	argp.add_argument(
		"-l", "--lower-left",
		help="coordinates of the lower left corner of the bounding box of the region that shapefiles should be processed for (default: %(default)s)",
		default="-180,-90"
	)
	
	argp.add_argument(
		"-u", "--upper-right",
		help="coordinates of the upper-right corner of the bounding box of the region that shapefiles should be processed for (default: %(default)s)",
		default="180,90"
	)
	
	args = argp.parse_args()
	
	if args.description:
		print(DESCRIPTION)
		sys.exit(0)

	src = args.input_folder
	dest = args.output_folder
	cache = args.cache_folder
	xll, yll = args.lower_left.split(",")
	xur, yur = args.upper_right.split(",")
	coords = {"xll": xll, "yll": yll, "xur": xur, "yur": yur}
	
	if not os.path.isdir(src):
		print(f"ERROR: input folder {args.input_folder} does not exist, exiting")
		sys.exit(1)
	
	if not os.path.isdir(dst):
		os.mkdirs(dst)
	
	if not os.path.isdir(cache):
		os.mkdirs(cache)
	
	shapefiles = shapefiles.find(src)
	categories = shapefiles.categorize(shapefiles)
	extents = shapefiles.get_extents(categorized)
	shapefiles = shapefiles.merge_slice(extents, coords)
	result = shapefiles.decode(shapefiles, dest)

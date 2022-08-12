#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Script that merges, slices, and decodes OSM shapefiles as needed by parsing the coordinates input and the extent of all shapefiles.

import os
import sys
import glob
import re
import argparse
import subprocess
import tempfile

from fgtools.utils import constants

DESCRIPTION = """
process-shapefiles.py - merges, slices, and decodes OSM shapefiles

IMPORTANT: CORINE shapefiles are NOT YET SUPPORTED !!!

This script recursively searches the specified input directory for files containing 'osm' and ending with '.shp'.
All that are found are then categorized into multiple categories - one for landuse, one for landmass, one for roads, etc.
For this reason, you may only remove the 'gis_' and '_free_1' parts from the shapefile's names !
Everything else in the name must be conserved in order for your resulting scenery not to have big areas of default landmass terrain !''

Then, for each shapefile in each category the extents will be queried using ogrinfo. To reduce processing time on subsequent runs, the results will be cached.
Then, the script will merge and slice the shapefiles for each category based on the coordinates you input.
It will merge / slice the files accordingly with ogr2ogr.
"""
#As the final step, the resulting shapefiles will be decoded into files that tg-constrcut can read using ogr-decode.
#"""
catnames = ["buildings_a", "landuse_a", "natural", "natural_a", "places", "places_a", "pofw", "pofw_a", "pois", "pois_a", "railways", "roads", "traffic", "traffic_a", "transport", "transport_a", "water_a", "waterways"]
tmpdir = tempfile.TemporaryDirectory()

def find(src):
	osm_shapefiles = []
	files = glob.glob(os.path.join(src, "**", "**.shp"))
	for file in files:
		if "osm" in os.path.split(file)[-1]:
			osm_shapefiles.append(file)
	
	return sorted(osm_shapefiles)

def categorize(shapefiles):
	categorized = dict((catname, []) for catname in catnames)
	
	for shapefile in shapefiles:
		name = os.path.split(shapefile)[-1].split(".")[0]
		
		name = re.sub(r"gis|osm|free|_(?!a)|\d", "", name) # gis_osm_landuse_a_free_1 becomes just landuse_a
		# Skip if the name is not a recognized catname
		if not name in catnames:
			continue
		
		categorized[name].append({"path": shapefile})
	return categorized

def get_extents(categorized):
	for category in categorized:
		for shapefile in categorized[category]:
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

def merge_slice(shapefiles, coords, dest):
	for category in shapefiles:
		print(f"Merging and slicing {category} …")
		dest_file = os.path.join(dest, category + ".shp")
		os.path.isfile(dest_file) and os.remove(dest_file)
		for shapefile in shapefiles[category]:
			cmd = f'ogr2ogr -f "ESRI Shapefile" "{dest_file}" "{shapefile["path"]}" -clipsrc {coords["xll"]} {coords["yll"]} {coords["xur"]} {coords["yur"]} -progress -lco ENCODING=UTF-8 -append'
			subprocess.run(cmd, shell=True)

#def decode(shapefiles, dest):
#	pass

if __name__ == "__main__":
	argp = argparse.ArgumentParser(description="process-shapefiles.py - merges, slices, and decodes OSM shapefiles")
	
	argp.add_argument(
		"-v", "--version",
		action="version",
		version=f"FGTools {'.'.join(map(str, constants.__version__))}"
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
		"-b", "--bbox",
		help="coordinates of the lbounding box of the region that shapefiles should be processed for (default: %(default)s)",
		default=[-180, -90, 180, 90],
		nargs=4,
		type=float
	)
	
	args = argp.parse_args()
	
	if args.description:
		print(DESCRIPTION)
		sys.exit(0)

	src = args.input_folder
	dest = args.output_folder
	coords = dict(zip(["xll", "yll", "xur", "yur"], args.bbox))
	
	if not os.path.isdir(src):
		print(f"ERROR: input folder {src} does not exist, exiting")
		sys.exit(1)
	
	if not os.path.isdir(dest):
		os.makedirs(dest)
	
	shapefiles = find(src)
	categories = categorize(shapefiles)
	#extents = get_extents(categorized)
	#shapefiles = merge_slice(extents, coords, dest)
	shapefiles = merge_slice(categories, coords, dest)
	#result = decode(shapefiles, dest)

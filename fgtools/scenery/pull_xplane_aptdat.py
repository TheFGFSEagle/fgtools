#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import sys
import argparse
import json
import io
import zipfile
import base64
import requests
import appdirs

def get_airports_list():
	os.makedirs(appdirs.user_cache_dir("fgtools"), exist_ok=True)
	airports_json_path = os.path.join(appdirs.user_cache_dir("fgtools"), "airports.json")
	if not os.path.isfile(airports_json_path):
		airports_json = requests.get("https://gateway.x-plane.com/apiv1/airports").json()
		with open(airports_json_path, "w") as f:
			json.dump(airports_json, f)
	else:
		with open(airports_json_path, "r") as f:
			airports_json = json.load(f)
	
	return airports_json["total"], airports_json["airports"]

def filter_airports_list(airports_count, airports_list, icaos, bbox):
	airports_list_filtered = []
	i = 0
	for airport in airports_list:
		print(f"Filtering airports … {i / airports_count * 100:.1f}% ({i} of {airports_count})\r", end="")
		i += 1
		airport_metadata = airport.get("metadata", {}) or {}
		if icaos and any(icao in (airport.get("AirportCode", None), airport_metadata.get("icao_code", None)) for icao in icaos):
			airports_list_filtered.append(airport)
		elif bbox:
			if bbox[1] < airport["Latitude"] < bbox[3] and bbox[0] < airport["Longitude"] < bbox[2]:
				airports_list_filtered.append(airport)
	print("Filtering airports … done                                                                                                                                  ")
	
	return airports_list_filtered

def write_aptdat_files(airports_list, output, txt_output, overwrite):
	airports_count = len(airports_list)
	i = 0
	for airport in airports_list:
		print(f"Downloading and writing airports … {i / airports_count * 100:.1f}% ({i} of {airports_count})\r", end="")
		i += 1
		airport_metadata = airport.get("metadata", {}) or {}
		icao_code = airport_metadata.get("icao_code", None) or airport["AirportCode"]
		if os.path.isfile(os.path.join(output, icao_code + ".dat")) and not overwrite:
			continue
		
		scenery_id = airport.get("RecommendedSceneryId", None)
		if not scenery_id:
			print("Airport", icao_code, "has no scenery - skipping                                                                                                             ")
			continue
		
		scenery_json = requests.get("https://gateway.x-plane.com/apiv1/scenery/" + str(scenery_id)).json()
		scenery_blob = io.BytesIO(base64.b64decode(scenery_json["scenery"]["masterZipBlob"]))
		with zipfile.ZipFile(scenery_blob, "r") as scenery_zip:
			try:
				scenery_dat = scenery_zip.open(icao_code + ".dat")
			except KeyError:
				pass
			else:
				with open(os.path.join(output, icao_code + ".dat"), "wb") as aptdat:
					aptdat.write(scenery_dat.read())
			
			if txt_output and os.path.isdir(txt_output):
				try:
					scenery_txt = scenery_zip.open(icao_code + ".txt")
				except KeyError:
					pass
				else:
					with open(os.path.join(txt_output, icao_code + ".txt"), "wb") as apttxt:
						apttxt.write(scenery_txt.read())
		
	print("Downloading and writing airports … done                                                                                                     ")

def main():
	argp = argparse.ArgumentParser(description="Pulls apt.dat files from the XPlane Gateway selected either by a bounding box or ICAO codes")
	
	argp.add_argument(
		"-i", "--icao",
		help="ICAO code(s) of the apt.dat files to be pulled",
		nargs="+"
	)
	
	argp.add_argument(
		"-b", "--bbox",
		help="All airports in the given bounding box will be pulled",
		nargs=4,
		type=float
	)
	
	argp.add_argument(
		"-o", "--output",
		help="Directory to put apt.dat files in",
		required=True
	)
	
	argp.add_argument(
		"-q", "--query",
		help="Don't write apt.dat files, only output a list of found airports",
		action="store_true"
	)
	
	argp.add_argument(
		"-t", "--txt-output",
		help="Where to write .txt files to (.txt files won't be written if this option is not specified or the directory doesn't exist)",
		default=""
	)
	
	argp.add_argument(
		"--overwrite",
		help="Whether to redownload and overwrite apt.dat files that already exist in OUTPUT",
		action="store_true"
	)
	
	args = argp.parse_args()
	
	if not args.icao and not args.bbox:
		argp.error("At least one of -i/--icao and -b/--bbox must be given !")
	
	if not os.path.isdir(args.output):
		argp.error(f"Output folder {args.output} does not exist - exiting")
	
	
	airports_count, airports_list = get_airports_list()
	airports_list_filtered = filter_airports_list(airports_count, airports_list, args.icao, args.bbox)
	
	if args.query:
		print("Airport code	ICAO code")
		for airport in airports_list_filtered:
			print(airport["AirportCode"] + "\t", (airport.get("metadata", {}) or {}).get("icao_code", "\t"), sep="\t")
	
	write_aptdat_files(airports_list_filtered, args.output, args.txt_output, args.overwrite)

if __name__ == "__main__":
	main()


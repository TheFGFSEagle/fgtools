#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import sys
import csv
import requests
import argparse
import shutil

from fgtools.utils.files import find_input_files
from fgtools.geo.coord import Coord
from fgtools.utils import constants

def _get_ourairports_csv(what):
	path = os.path.join(constants.CACHEDIR, what + ".csv")
	if not os.path.isfile(path):
		with open(path, "w") as f:
			f.write(requests.get(f"https://davidmegginson.github.io/ourairports-data/{what}.csv").content.decode())
	f = open(path, "r", newline="")
	return list(csv.DictReader(f))[1:]

def get_ourairports_icao(airport, csv):
	c = Coord(airport["lon"], airport["lat"])
	matches = []
	for line in csv:
		d = c.distance_km(Coord(float(line["longitude_deg"]), float(line["latitude_deg"])))
		if d <= 10:
			matches.append({"distance": d, "icao": line["gps_code"] or line["local_code"] or line["ident"]})
	matches.sort(key=lambda m: m["distance"])
	if len(matches) and matches[0]["icao"]:
		if len(airport["icao"]) != 4:
			airport["newicao"] = matches[0]["icao"]
	else:
		print(f"No matching airport found for {airport['icao']} - skipping", end=" " * 100 + "\n")
	return airport

def process(files, output):
	csv = _get_ourairports_csv("airports")
	i = 0
	n = 0
	skipped = 0
	total = len(files)
	files_d = {}
	for p in files:
		print(f"Parsing files … {i / total * 100:.1f}% ({i} of {total} done, found {n} airports)", end="\r")
		i += 1
		file_d = {"lines": [], "airports": {}}
		with open(p, "r") as f:
			file_d["lines"] = list(map(lambda l: list(filter(None, l)), map(lambda s: s.split(" "), filter(None, map(str.strip, f.readlines())))))
		curicao = ""
		for line in file_d["lines"]:
			if line[0] in ("1", "16", "17"):
				curicao = line[4]
				skip = False
				file_d["airports"][curicao] = {"icao": curicao}
				n += 1
			elif line[0] == "1302":
				if line[1] == "datum_lon":
					if len(line) < 3:
						continue
					file_d["airports"][curicao]["lon"] = float(line[2])
				if line[1] == "datum_lat":
					if len(line) < 3:
						continue
					file_d["airports"][curicao]["lat"] = float(line[2])
			elif line[0] in ("100", "101", "102") and not ("lon" in file_d["airports"][curicao] and "lat" in file_d["airports"][curicao]):
				# no datum_lon / datum_lat found, approximate airport position from first runway / helipad found
				if line[0] == "100": # land runway
					lon = (float(line[10]) + float(line[19])) / 2
					lat = (float(line[9]) + float(line[18])) / 2
				elif line[0] == "101": # water runway
					lon = (float(line[5]) + float(line[8])) / 2
					lat = (float(line[4]) + float(line[7])) / 2
				else: # helipad
					lon = float(line[3])
					lat = float(line[2])
				file_d["airports"][curicao]["lon"] = lon
				file_d["airports"][curicao]["lat"] = lat
			
		for icao in list(file_d["airports"].keys()):
			if not ("lon" in file_d["airports"][icao] and "lat" in file_d["airports"][icao]):
				print(f"Unable to get longitude / latitude of airport {curicao} in file {p} - skipping", end=" " * 100 + "\n")
				del file_d["airports"][icao]
				n -= 1
				skipped += 1
		
		files_d[p] = file_d
	print(f"Parsing files … {i / total * 100:.1f}% ({i} of {total} done, found {n} airports, skipped {skipped})", end=" " * 100 + "\n")
	
	i = 0
	total = n
	for p in files_d:
		for icao in files_d[p]["airports"]:
			print(f"Getting ICAOs for airports … {i / total * 100:.1f}% ({i} of {total} done)", end="\r")
			i += 1
			files_d[p]["airports"][icao] = get_ourairports_icao(files_d[p]["airports"][icao], csv)
	print(f"Getting ICAOs for airports … {i / total * 100:.1f}% ({i} of {total} done)", end=" " * 100 + "\n")
	
	i = 0
	total = len(files_d)
	for p in files_d:
		print(f"Writing new apt.dat files … {i / total * 100:.1f}% ({i} of {total} done)", end="\r")
		i += 1
		if output == None:
			outp = p
		else:
			outp = os.path.join(output, os.path.split(p)[-1])
		
		parts = os.path.split(outp)
		prefix, newname = os.path.join(*parts[:-1]), parts[-1]
		if len(files_d[p]["airports"]) > 0 and newname != "apt.dat":
			firsticao = list(files_d[p]["airports"].keys())[0]
			if "newicao" in files_d[p]["airports"][firsticao]:
				newname = files_d[p]["airports"][firsticao]["newicao"] + ".dat"
		newoutp = os.path.join(prefix, newname)
		
		with open(outp, "w") as f:
			for line in files_d[p]["lines"]:
				if line[0] in ("1", "16", "17") and line[4] in files_d[p]["airports"] and "newicao" in files_d[p]["airports"][line[4]]:
					line[4] = files_d[p]["airports"][line[4]]["newicao"]
				f.write(" ".join(line) + "\n")
		
		if outp != newoutp:
			print(f"Renaming file: {outp} -> {newoutp}", end=" " * 100 + "\n")
			shutil.move(outp, newoutp)
	print(f"Writing new apt.dat files … {i / total * 100:.1f}% ({i} of {total} done)", end=" " * 100 + "\n")

def main():
	argp = argparse.ArgumentParser(description="Fix apt.dat ICAO's - some apt.dat files from the XPlane gateway have them of the form XAY0016 - this script gets the right ICAO from OurAirports data (if the airport is found there)")
	
	argp.add_argument(
		"-i", "--input",
		help="Input apt.dat file(s) / folder(s) containing apt.dat files",
		required=True,
		nargs="+"
	)
	
	argp.add_argument(
		"-o", "--output",
		help="Output folder for the modified apt.dat files - omit to edit the files in-place",
		default=None
	)
	
	args = argp.parse_args()
	
	infiles = find_input_files(args.input)
	process(infiles, args.output)

if __name__ == '__main__':
	main()




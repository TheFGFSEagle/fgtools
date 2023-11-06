#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import sys
import argparse
import requests
import csv
import re
import logging
import math

from OSMPythonTools import overpass

from fgtools.geo import coord, rectangle
from fgtools.utils import files
from fgtools import aptdat
from fgtools.utils import constants
from fgtools.utils import unit_convert

osmapi = overpass.Overpass()

def parse_runway_id(id):
	which, heading = "", 0
	if id[-1] in ("L", "C", "R"):
		which = id[-1]
	try:
		if which:
			heading = int(id[:-1])
		else:
			heading = int(id)
	except ValueError:
		heading = 0
	return heading * 10, which

def parse_surface_type(surface):
	if re.search("pem|mac|sealed|bit|asp(h)?(alt)?|tarmac", surface) or surface in ("b"):
		surface = "Asphalt"
	elif re.search("wood|cement|bri(ck)?|hard|paved|pad|psp|met|c[o0]n(c)?", surface):
		surface = "Concrete"
	elif re.search("rock|gvl|grvl|gravel|pi(ç|c)", surface):
		surface = "Gravel"
	elif re.search("tr(ea)?t(e)?d|san(d)?|ter|none|cor|so(ft|d|il)|earth|cop|com|per|ground|silt|cla(y)?|dirt|turf", surface):
		surface = "Dirt"
	elif re.search("gr(a*)?s|gre", surface) or surface in ("g"):
		surface = "Grass"
	elif re.search("wat(er)?", surface):
		surface = "Water"
	elif re.search("sno|ice", surface):
		surface = "SnowIce"
	else:
		surface = "Unknown"
	return surface

def _get_ourairports_csv(what):
	path = os.path.join(constants.CACHEDIR, what + ".csv")
	if not os.path.isfile(path):
		with open(path, "w") as f:
			f.write(requests.get(f"https://davidmegginson.github.io/ourairports-data/{what}.csv").content.decode())
	f = open(path, "r", newline="")
	return list(csv.DictReader(f))[1:]

def get_ourairports_airports(bbox=None, icaos=[]):
	if not (bbox or icaos):
		raise TypeError("both bbox and icaos are None")
	csv = _get_ourairports_csv("airports")
	airports = []
	print("Creating airports from OurAirports data … ", end="")
	for line in csv:
		type = aptdat.AirportType.Land
		if "sea" in line["type"]:
			type = aptdat.AirportType.Sea
		elif "heli" in line["type"]:
			type = aptdat.AirportType.Heli
		
		code = line["gps_code"] or line["local_code"] or line["ident"]
		if not code:
			continue
		airport = {"ident": line["ident"], "airport": aptdat.Airport(int(line["elevation_ft"] or 0), code,
												line["name"], float(line["longitude_deg"]),
												float(line["latitude_deg"]), type=type)}
		
		if code in icaos:
			icaos.remove(code)
			airports.append(airport)
		elif bbox and bbox.is_inside(coord.Coord(airport["airport"].lon, airport["airport"].lat)):
			airports.append(airport)
	print(f"done - found {len(airports)} airports for the given bounding box / ICAO")
	return airports

def get_osm_elements_near_airport(airport, what, query, element_type, radius=10000, max_retries=10):
	left = coord.Coord(airport.lon, 0).apply_angle_distance_m(-90, radius).lon
	right = coord.Coord(airport.lon, 0).apply_angle_distance_m(90, radius).lon
	upper = coord.Coord(0, airport.lat).apply_angle_distance_m(0, radius).lat
	lower = coord.Coord(0, airport.lat).apply_angle_distance_m(180, radius).lat
	query = overpass.overpassQueryBuilder(bbox=[lower, left, upper, right], elementType=element_type,
									selector=query, out="center")
	result = -1
	retries = 0
	while result == -1 and retries < max_retries:
		try:
			if element_type == "node":
				result = osmapi.query(query, timeout=60).nodes()
			elif element_type == "way":
				result = osmapi.query(query, timeout=60).ways()
			elif element_type == "relations":
				result = osmapi.query(query, timeout=60).relations()
			else:
				result = []
				qresult = osmapi.query(query, timeout=100)
				if not qresult:
					result = None
					break
				for etype in element_type:
					result += getattr(qresult, etype + "s")() or []
		except Exception as e:
			if "timeout" in str(e.args).lower():
				result = -1
			else:
				raise e
		retries += 1
	if result == -1:
		print(f"API query for OSM {what} data for airport {airport.icao} timed out {retries} times - won't retry", end=" " * 100 + "\n")
		result = []
	if result == None:
		result = []
		print(f"No OSM {what} data found for airport {airport.icao}", end=" " * 100 + "\n")
	return result
	
def add_osm_runways(airport):
	result = get_osm_elements_near_airport(airport["airport"], "runway", '"aeroway"="runway"', "way")
	osmways = []
	for way in result:
		first, last = way.nodes()[0], way.nodes()[-1]
		if first.id() == last.id():
			print("Got a runway mapped as area from OSM - not supported yet", end=" " * 100 + "\n")
			continue
		first = coord.Coord(first.lon(), first.lat())
		last = coord.Coord(last.lon(), last.lat())
		heading = first.angle(last)
		if heading > 180:
			first, last = last, first
		heading -= 180
		center = rectangle.Rectangle(last, first).midpoint()
		distance = coord.Coord(airport["airport"].lon, airport["airport"].lat).distance_m(center)
		osmways.append({"distance": distance, "heading": heading, "way": way, "first": first, "last": last})
	osmways.sort(key=lambda r: r["distance"])
	for i, runway in enumerate(airport["runways"]):
		osmways_filtered = []
		for osmway in osmways:
			if "ref" in osmway["way"].tags():
				# water runways somtimes have N, NE, etc. as identifier instead of 36, 04, etc.
				mapping = {"N": "36", "NE": "04", "E": "09", "SE": "13", "S": "18", "SW": "22", "W": "27", "NW": "31"}
				if runway["le_ident"] in mapping:
					runway["le_ident"] = mapping[runway["le_ident"]]
				if runway["he_ident"] in mapping:
					runway["he_ident"] = mapping[runway["he_ident"]]
				
				if osmway["way"].tags()["ref"] == runway["le_ident"] + "/" + runway["he_ident"]:
					osmways_filtered = [osmway]
					break
			else:
				heading, which = parse_runway_id(runway["le_ident"])
				if heading <= osmway["heading"] < heading + 10:
					if not which:
						osmways_filtered = [osmway]
						break
					else:
						osmways_filtered.append(osmway)
						if len(osmways_filtered) == 3:
							break
		if len(osmways_filtered) == 0:
			print("No OSM data found for runway", runway["le_ident"], "at airport", airport["airport"].icao, end=" " * 100 + "\n")
		elif len(osmways_filtered) == 1: # just one matching runway - nothing left to do
			runway["osmway"] = osmways_filtered[0]
		elif len(osmways_filtered) == 2: # two parallel runways - sort from left to right and pick the right one
			center1 = coord.Coord(osmways_filtered[0].centerLon(), osmways_filtered[0].centerLat())
			center2 = coord.Coord(osmways_filtered[1].centerLon(), osmways_filtered[1].centerLat())
			heading, which = parse_runway_id(runway["le_ident"])
			rel_bearing = center1.angle(center2) - heading
			index = 0
			if rel_bearing > 0:
				index = 0 if which == "L" else 1
			else:
				index = 1 if which == "L" else 0
			runway["osmway"] = osmways_filtered[index]
		else: # three or more parallel runways - sort the first three from left to right and pick the right one
			center1 = coord.Coord(osmways_filtered[0].centerLon(), osmways_filtered[0].centerLat())
			center2 = coord.Coord(osmways_filtered[1].centerLon(), osmways_filtered[1].centerLat())
			center3 = coord.Coord(osmways_filtered[2].centerLon(), osmways_filtered[2].centerLat())
			heading, which = parse_runway_id(runway["le_ident"])
			rel_bearing1 = center1.angle(center2) - heading
			rel_bearing2 = center2.angle(center3) - heading
			index = 0
			if rel_bearing1 > 0 and rel_bearing2 > 0:
				index = "LCR".find(which)
			elif rel_bearing1 <= 0 and rel_bearing2 > 0:
				index = "CLR".find(which)
			elif rel_bearing1 > 0 and rel_bearing2 <= 0:
				index = "LRC".find(which)
			else:
				index = "RCL".find(which)
			runway["osmway"] = osmways_filtered[index]
		
		if not runway["le_longitude_deg"] or not runway["he_longitude_deg"]:
			if "osmway" in runway:
				runway["le_heading_degT"] = runway["osmway"]["heading"]
				runway["he_heading_degT"] = runway["osmway"]["heading"] + 180
				runway["le_longitude_deg"] = runway["osmway"]["first"].lon
				runway["le_latitude_deg"] = runway["osmway"]["first"].lat
				runway["he_longitude_deg"] = runway["osmway"]["last"].lon
				runway["he_latitude_deg"] = runway["osmway"]["last"].lat
			else:
				print("No threshold information found for runway", runway["le_ident"], "at", airport["airport"].icao, "- removing !",  end=" " * 100 + "\n")
				airport["runways"][i] = None
	airport["runways"] = list(filter(None, airport["runways"]))

def add_osm_helipads(airport):
	result = get_osm_elements_near_airport(airport["airport"], "helipad", '"aeroway"="helipad"', ["node", "way"])
	osmhelipads = []
	counter = 0
	for element in result:
		if element.type() == "node":
			c = coord.Coord(element.lon(), element.lat())
			radius = 0
		else:
			lon_sum = lat_sum = 0
			divider = 0
			for node in element.nodes():
				lon_sum += node.lon()
				lat_sum += node.lat()
				divider += 1
			c = coord.Coord(lon_sum / divider, lat_sum / divider)
			dist_sum = 0
			for node in element.nodes():
				dist_sum += c.distance_m(coord.Coord(node.lon(), node.lat()))
			radius = dist_sum / divider
		surface = ""
		if "surface" in element.tags():
			surface = element.tags()["surface"]
		lit = None
		if "lit" in element.tags():
			lit = element.tags()["lit"] == "yes"
		id = f"H{counter}"
		counter += 1
		osmhelipads.append({"coord": c, "radius": radius, "surface": surface, "id": id, "lit": None})
	with_lon_lat = []
	without_lon_lat = []
	while len(airport["helipads"]):
		helipad = airport["helipads"].pop()
		if helipad["le_longitude_deg"] and helipad["le_latitude_deg"]:
			with_lon_lat.append(helipad)
		else:
			without_lon_lat.append(helipad)
	for helipad in with_lon_lat:
		if len(osmhelipads) > 0:
			for osmhelipad in osmhelipads:
				osmhelipad["distance"] = osmhelipad["coord"].distance_m(coord.Coord(float(helipad["le_longitude_deg"]),
																					float(helipad["le_latitude_deg"])))
			osmhelipads.sort(key=lambda d: d["distance"])
			helipad["osmhelipad"] = osmhelipads.pop(0)
		else:
			helipad["osmhelipad"] = {}
	
	for osmhelipad in osmhelipads:
		osmhelipad["distance"] = osmhelipad["coord"].distance_m(coord.Coord(airport["airport"].lon, airport["airport"].lat))
	osmhelipads.sort(key=lambda d: d["distance"])
	for i, helipad in enumerate(without_lon_lat):
		if len(osmhelipads) > 0:
			helipad["osmhelipad"] = osmhelipads.pop(0)
			helipad["le_longitude_deg"] = helipad["osmhelipad"]["coord"].lon
			helipad["le_latitude_deg"] = helipad["osmhelipad"]["coord"].lat
		else:
			without_lon_lat[i] = None
	if None in without_lon_lat:
		print(f"No position information found for {without_lon_lat.count(None)} helipad(s) at {airport['airport'].icao} - removing", end=" " * 100 + "\n")
	without_lon_lat = list(filter(None, without_lon_lat))
	
	airport["helipads"] = with_lon_lat + without_lon_lat
	
	for osmhelipad in osmhelipads:
		helipad = {"airport_ident": airport["airport"].icao, "le_longitude_deg": osmhelipad["coord"].lon,
					"le_latitude_deg": osmhelipad["coord"].lat, "lighted": osmhelipad["lit"], "surface": osmhelipad["surface"],
					"length_ft": 0, "width_ft": 0, "osmhelipad": osmhelipad}

def add_ourairports_runways(airports):
	csv = _get_ourairports_csv("runways")
	i = 0
	total = len(airports)
	for airport in airports:
		print(f"Extracting runways from OurAirports data … {i / total * 100:.1f}% ({i} of {total} airports done)", end="\r")
		i += 1
		runways = []
		helipads = []
		for line in csv:
			if line["airport_ident"] == airport["ident"]:
				if re.match(line["le_ident"], "H[0-9]*"):
					helipads.append(line)
				else:
					runways.append(line)
			else:
				if runways or helipads:
					break
		airport["runways"] = runways
		airport["helipads"] = helipads
		add_osm_runways(airport)
		add_osm_helipads(airport)
		if len(airport["runways"]) == 0 and len(airport["helipads"]) == 0:
			print(f"Removing airport {airport['airport'].icao} since it has no runways / helipads !", end=" " * 100 + "\n")
			airports[i - 1] = None
			continue
		
		for runway in airport["runways"]:
			surface = parse_surface_type(runway["surface"].lower())
			if surface == "Unknown":
				if "osmway" in runway:
					if "surface" in runway["osmway"]["way"].tags():
						surface = parse_surface_type(runway["osmway"]["way"].tags()["surface"])
			
			if surface == "Unknown":
				if (int(runway["length_ft"] or 0) > 1500 and int(runway["width_ft"] or 0) > 30) or int(runway["lighted"]):
					surface = "Asphalt"
				else:
					surface = "Dirt"
				print("Unknown surface type:", runway["surface"], "for runway", runway["le_ident"], "at airport", airport["airport"].icao, "- falling back to", surface, end=" " * 100 + "\n")
			runway["surface"] = surface
	print(f"Extracting runways from OurAirports data … {i / total * 100:.1f}% ({i} of {total} airports done)", end="\r\n")
	
	airports = list(filter(None, airports))
	
	i = 0
	total = len(airports)
	for airport in airports:
		print(f"Creating runways … {i / total * 100}% ({i} of {total} airports done)", end="\r")
		i += 1
		for runway in airport["runways"]:
			width = runway["width_ft"]
			if width != "":
				width = float(width)
			elif "osmway" in runway and "width" in runway["osmway"]["way"].tags():
				width = round(float(runway["osmway"]["way"].tags()["width"]), 2)
			else:
				print(f"No width found for runway {runway['le_ident']} at airport {airport['airport'].icao} - guessing from length", end=" " * 100 + "\n")
				width = math.sqrt(int(runway["length_ft"] or 0))
			if runway["surface"] == "water":
				runway = aptdat.WaterRunway(unit_convert.ft2m(width),
							runway["le_ident"], float(runway["le_longitude_deg"]), float(runway["le_latitude_deg"]),
							runway["he_ident"], float(runway["he_longitude_deg"]), float(runway["he_latitude_deg"]),
							perimeter_buoys=True)
			else:
				center_lights = edge_lights = bool(runway["lighted"])
				if center_lights and surface not in ("Asphalt", "Concrete"):
					center_lights = edge_lights = False
				distance_signs = int(runway["length_ft"] or 0) > 4000
				tdz_lights = runway["surface"] in ("Asphalt", "Concrete")
				markings = aptdat.RunwayMarkingCode.Visual
				if runway["surface"] not in ("Asphalt", "Concrete"):
					markings = aptdat.RunwayMarkingCode.NoMarkings
				elif 4000 < int(runway["length_ft"] or 0) < 6000:
					markings = aptdat.RunwayMarkingCode.NonPrecision
				elif int(runway["length_ft"] or 0) >= 6000:
					markings = aptdat.RunwayMarkingCode.Precision
				reil_type = aptdat.REILCode.NoREIL
				if markings == aptdat.RunwayMarkingCode.NonPrecision:
					reil_type = aptdat.REILCode.UnidirREIL
				
				runway = aptdat.LandRunway(unit_convert.ft2m(width), getattr(aptdat.SurfaceCode, runway["surface"]),
							runway["le_ident"], float(runway["le_longitude_deg"]), float(runway["le_latitude_deg"]),
							runway["he_ident"], float(runway["he_longitude_deg"]), float(runway["he_latitude_deg"]),
							center_lights=center_lights, edge_lights=edge_lights, distance_signs=distance_signs,
							displ_thresh1=float(runway["le_displaced_threshold_ft"] or 0), tdz_lights1=tdz_lights,
							markings1=markings, reil_type1=reil_type,
							displ_thresh2=float(runway["he_displaced_threshold_ft"] or 0), tdz_lights2=tdz_lights,
							markings2=markings, reil_type2=reil_type)
			airport["airport"].add_runway(runway)
	print(f"Creating runways … {i / total * 100}% ({i} of {total} airports done)")
	
	i = 0
	for airport in airports:
		print("Creating helipads … {i / total * 100}% ({i} of {total} airports done)", end="\r")
		i += 1
		for helipad in airport["helipads"]:
			if helipad["width_ft"]:
				width = round(float(helipad["width_ft"]), 2)
			elif "radius" in helipad["osmhelipad"]:
				width = radius * 2
			else:
				width = 50
				print((f"Unable to get width for for helipad {helipad['le_ident']} at airport {airport['airport'].icao}" +
						f" - setting to {width} ft"), end=" " * 100 + "\n")
			if helipad["length_ft"]:
				length = round(float(helipad["length_ft"]), 2)
			elif "radius" in helipad["osmhelipad"]:
				length = radius * 2
			else:
				length = 50
				print((f"Unable to get length for for helipad {helipad['le_ident']} at airport {airport['airport'].icao}" +
						f" - setting to {length} ft"), end=" " * 100 + "\n")
						
			lighted = bool(int(helipad["lighted"]))
			surface = parse_surface_type(helipad["surface"])
			if surface == "Unknown" and "surface" in helipad["osmhelipad"]:
				surface = parse_surface_type(helipad["osmhelipad"]["surface"])
				if surface == "Unknown":
					if lighted:
						surface = "Asphalt"
					else:
						surface = "Grass"
					
					print((f"Unknown surface type {helipad['surface']} for helipad {helipad['le_ident']} at" + 
							f" airport {airport['airport'].icao} - setting to {surface}"), end=" " * 100 + "\n")
			
			if surface not in ("Concrete", "Asphalt"):
				lighted = False
			print(helipad)
			helipad = aptdat.Helipad(helipad["id"], float(helipad["le_longitude_deg"]), float(helipad["le_latitude_deg"]), 0,
									unit_convert.ft2m(length), unit_convert.ft2m(width), surface, edge_lights=lighted)
			airport["airport"].add_helipad(helipad)
		airports[i - 1] = airport["airport"]
	return airports

def query_airports_by_icaos(icaos):
	# remove doubles
	icaos = list(set(icaos))
	ourairports = get_ourairports_airports(icaos=icaos)
	ourairports = add_ourairports_runways(ourairports)
	return ourairports

def query_airports_by_bbox(left, lower, right, upper):
	ourairports = get_ourairports_airports(bbox=rectangle.Rectangle(coord.Coord(left, lower), coord.Coord(right, upper)))
	ourairports = add_ourairports_runways(ourairports)
	return ourairports

def check_aptdat_written_by_this(path):
	with open(path, "r") as f:
		i = 0
		while i < 2:
			fl = f.readline()
			if fl:
				i += 1
			if "osm2aptdat.py" in fl:
				return True
	return False

def write_aptdat_files(output, airports, merge=False):
	writer = aptdat.ReaderWriterAptDat(file_header="Generated from OSM and OurAirports data by fgtools.osm2aptdat.py")
	writer.add_airports(airports)
	writer.write(output, merge=merge, overwrite_func=check_aptdat_written_by_this)

def main():
	logging.getLogger("OSMPythonTools").setLevel(logging.FATAL)
	
	argp = argparse.ArgumentParser(description="query airports from OSM and convert the results to apt.dat files")
	
	bbox_icao_group = argp.add_mutually_exclusive_group(required=True)
	bbox_icao_group.add_argument(
		"-b", "--bbox",
		help="GPS coordinates of the lower left and upper right corners of the bounding box within which all airports should be processed",
		nargs=4,
		metavar=("LL_LON", "LL_LAT", "UR_LON", "UR_LAT"),
		type=float,
	)
	
	bbox_icao_group.add_argument(
		"-i", "--icao",
		help="ICAO code(s) of the airport(s) to process",
		nargs="+"
	)
	
	argp.add_argument(
		"-m", "--merge",
		help="Merge all airports into one big apt.dat file instead of writing one file for each airport",
		action="store_true"
	)
	
	argp.add_argument(
		"-o", "--output",
		help="directory to put apt.dat files into",
		required=True
	)
	
	args = argp.parse_args()
	
	if args.icao:
		airports = query_airports_by_icaos(args.icao)
	else:
		airports = query_airports_by_bbox(left=args.bbox[0], lower=args.bbox[1], right=args.bbox[2], upper=args.bbox[3])
	
	write_aptdat_files(args.output, airports, merge=args.merge)

if __name__ == '__main__':
	main()


	

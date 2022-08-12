#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import sys
import argparse
import statistics

from fgtools.utils.files import find_input_files
from fgtools import utils
from fgtools.utils import geo
from fgtools.utils import unit_convert

def format_coord(coord, lonlat):
	prefix = {"lon": ["E", "W"], "lat": ["N", "S"]}[lonlat][coord < 0]
	
	i = abs(int(coord))
	f = abs(coord) - i
	return f"{prefix}{i} {f * 60:.8f}"

def get_icao_xml_path(icao, what):
	if len(icao) == 3:
		return f"{icao[0]}/{icao[1]}/{icao}.{what}.xml"
	else:
		return f"{icao[0]}/{icao[1]}/{icao[2]}/{icao}.{what}.xml"

class Parking:
	def __init__(self, index, type, name, lon, lat, hdg, radius=7.5, pushback_route=False, airline_codes=[]):
		self.index = index
		self.type = type
		self.name = name
		self.lon = lon
		self.lat = lat
		self.hdg = hdg
		self.radius = radius
		self.pushback_route = pushback_route
		self.airline_codes = airline_codes
	
	@staticmethod
	def get_radius(code):
		return {"A": 7.5, "B": 14, "C": 18, "D": 26, "E": 33, "F": 40}[code]
	
	def __repr__(self):
		return (f'		<parking index="{self.index}" type="{self.type}" name="{self.name}" lon="{format_coord(self.lon, "lon")}"' +
				f' lat="{format_coord(self.lat, "lat")}" heading="{self.hdg}" radius="{self.radius}"' +
				f' pushBackRoute="{self.pushback_route}" airlineCodes="{",".join(self.airline_codes)}"/>\n')

class TaxiNode:
	def __init__(self, lon, lat, index):
		self.index = index
		self.lon = lon
		self.lat = lat
		self.on_runway = None
		self.holdPointType = "none"
	
	def __bool__(self):
		return self.on_runway != None
	
	def __repr__(self):
		return f'		<node index="{self.index}" lon="{format_coord(self.lon, "lon")} ' + 
				f'lat="{format_coord(self.lat, "lat)}" isOnRunway="{int(self.on_runway)}" holdPointType="{self.holdPointType}"/>'

class TaxiEdge:
	def __init__(self, begin, end, is_on_runway, name):
		self.begin = begin
		self.end = end
		self.name = name
		self.is_on_runway = is_on_runway
		self.is_pushback_route = None
	
	def __bool__(self):
		return self.is_pushback_route != None
	
	def __repr__(self):
		return f'		<arc begin="{self.begin}" end="{self.end}" ' + 
				f'isPushBackRoute="{int(self.is_pushback_route)}" name="{self.name}"/>

class Runway:
	def __init__(self, id1, lon1, lat1, displ1, stopway1, id2, lon2, lat2, displ2, stopway2):
		self.lon1 = lon1
		self.lat1 = lat1
		self.id1 = id1
		self.displ1 = displ1
		self.stopway1 = stopway1
		self.lon2 = lon2
		self.lat2 = lat2
		self.id2 = id2
		self.displ2 = displ2
		self.stopway2 = stopway2
	
	def get_length_m(self):
		return geo.great_circle_distance_m(self.lon1, self.lat1, self.lon2, self.lat2)
	
	def get_length_ft(self):
		return unit_convert.m2ft(self.get_length_m())
	
	def get_heading1_deg(self):
		return geo.get_bearing_deg(self.lon1, self.lat1, self.lon2, self.lat2)
	
	def get_heading2_deg(self):
		brg = self.get_heading1_deg() + 180
		while brg >= 360:
			brg -= 360
		return brg
	
	def __repr__(self):
		return f"""	<runway>
		<threshold>
			<lon>{self.lon1}</lon>
			<lat>{self.lat1}</lat>
			<rwy>{self.id1}</rwy>
			<hdg-deg>{self.get_heading1_deg():.2f}</hdg-deg>
			<displ-m>{self.displ1}</displ-m>
			<stopw-m>{self.stopway1}</stopw-m>
		</threshold>
		<threshold>
			<lon>{self.lon2}</lon>
			<lat>{self.lat2}</lat>
			<rwy>{self.id2}</rwy>
			<hdg-deg>{self.get_heading2_deg():.2f}</hdg-deg>
			<displ-m>{self.displ2}</displ-m>
			<stopw-m>{self.stopway2}</stopw-m>
		</threshold>
	</runway>
"""

class WaterRunway(Runway):
	def __init__(self, id1, lon1, lat1, id2, lon2, lat2):
		Runway.__init__(self, id1, lon1, lat1, 0, 0, id2, lon2, lat2, 0, 0)

class Tower:
	def __init__(self, lon, lat, agl):
		self.lon = lon
		self.lat = lat
		self.agl = agl
	
	def __repr__(self):
		return f"""	<tower>
		<twr>
			<lon>{self.lon}</lon>
			<lat>{self.lat}</lat>
			<elev-m>{self.agl}</elev-m>
		</twr>
	</tower>
"""

class ILS:
	def __init__(self):
		self.lon1 = None
		self.lat1 = None
		self.rwy1 = None
		self.hdg1 = None
		self.elev1 = None
		self.ident1 = None
		self.lon2 = None
		self.lat2 = None
		self.rwy2 = None
		self.hdg2 = None
		self.elev2 = None
		self.ident2 = None
	
	def set_data1(self, lon, lat, rwy, hdg, ident):
		self.lon1 = lon
		self.lat1 = lat
		self.rwy1 = rwy
		self.hdg1 = hdg
		self.ident1 = ident
	
	def set_data2(self, lon, lat, rwy, hdg, ident):
		self.lon2 = lon
		self.lat2 = lat
		self.rwy2 = rwy
		self.hdg2 = hdg
		self.ident2 = ident
	
	def __repr__(self):
		s = ""
		
		if None not in (self.lon1, self.lat1, self.rwy1, self.hdg1, self.elev1, self.ident1):
			s += f"""	<ils>
			<lon>{self.lon1}</lon>
			<lat>{self.lat1}</lat>
			<rwy>{self.rwy1}</rwy>
			<hdg-deg>{self.hdg1:.2f}</hdg-deg>
			<elev-m>{self.elev1}</elev-m>
			<nav-id>{self.ident1}</nav-id>
		</ils>
"""
		if None not in (self.lon2, self.lat2, self.rwy2, self.hdg2, self.elev2, self.ident2):
			s += """		<ils>
			<lon>{self.lon2}</lon>
			<lat>{self.lat2}</lat>
			<rwy>{self.rwy2}</rwy>
			<hdg-deg>{self.hdg2:.2f}</hdg-deg>
			<elev-m>{self.elev2}</elev-m>
			<nav-id>{self.ident2}</nav-id>
		</ils>
"""
		
		if s:
			s = f"	<runway>\n{s}	</runway>\n"
		
		return s
	
	def __bool__(self):
		return (None not in (self.lon1, self.lat1, self.rwy1, self.hdg1, self.ident1)) \
			or (None not in (self.lon2, self.lat2, self.rwy2, self.hdg2, self.ident2))
	

def parse_aptdat_files(files, nav_dat, print_runway_lengths):
	parkings = {}
	taxi_nodes = {}
	taxi_edges = {}
	runways =  {}
	towers = {}
	ils_d = {}
	
	print("Parsing nav.dat … ", end="")
	with open(nav_dat, "r", encoding="ISO-8859-1") as f:
		nav_ils = list(map(str.split, filter(lambda s: s.startswith("4"), f.readlines())))
		for i in range(0, len(nav_ils)):
			nav_ils[i] = list(filter(None, nav_ils[i]))
	print("done")
	
	runway_lengths = []
	
	i = 1
	total = len(files)
	for path in files:
		print(f"\rParsing apt.dat files … {i / total * 100:.1f}% ({i} of {total})", end="")
		with open(path, "r") as f:
			aptdat = list(map(str.split, filter(None, map(str.strip, f.readlines()))))
		
		icao = os.path.splitext(os.path.split(path)[-1])[0]
		parkings[icao] = []
		taxi_nodes[icao] = []
		taxi_edges[icao] = []
		runways[icao] = []
		ils_d[icao] = []
		
		for line in aptdat:
			try:
				line[0] = int(line[0])
			except ValueError:
				continue
			
			if line[0] == 1300: # parking
				parkings[icao].append(Parking(len(parkings[icao]), line[4], " ".join(line[6:]), float(line[2]), float(line[1]), int(float(line[3]))))
			elif line[0] == 1301: # parking metadata
				parkings[icao][-1].radius = Parking.get_radius(line[1])
				if len(line) == 4:
					parkings[icao][-1].airline_codes = line[3].split(",")
			elif line[0] == 100: # land runway
				runway = Runway(line[8], float(line[10]), float(line[9]), float(line[11]), float(line[12]), 
								line[17], float(line[19]), float(line[18]), float(line[20]), float(line[21]))
				
				if print_runway_lengths:
					runway_lengths.append({"icao": icao, "length-ft": runway.get_length_ft(),
											"lon": (runway.lon1 + runway.lon2) / 2, "lat": (runway.lat1 + runway.lat2) / 2})
				
				runways[icao].append(runway)
				
				ils = ILS()
				for il in nav_ils:
					if il[8] == icao:
						if il[9] == line[8]:
							ils.set_data1(float(line[10]), float(line[9]), line[8], runway.get_heading1_deg(), il[7])
						elif il[9] == line[17]:
							ils.set_data2(float(line[19]), float(line[18]), line[17], runway.get_heading2_deg(), il[7])
				 
				if ils:
					ils_d[icao].append(ils)
			
			elif line[0] == 101: # water runway
				runways[icao].append(WaterRunway(line[3], float(line[5]), float(line[4]), line[6], float(line[8]), float(line[7])))
			elif line[0] == 14:
				towers[icao] = Tower(float(line[2]), float(line[1]), float(line[3]))
			elif line[0] == 1201: # taxi node
				taxi_nodes[icao].append(TaxiNode(float(line[2], float(line[1]), len(taxi_nodes[icao]))))
			elif line[0] == 1202: # taxi edge
				taxi_edges[icao].append(TaxiEdge(int(line[1], int(line[2]), line[4] == "runway", line[5])))
		
		if not icao in towers and len(runways[icao]) > 0:
			runway_lons = []
			runway_lats = []
			runway_hdgs = []
			for runway in runways[icao]:
				runway_lons += [runway.lon1, runway.lon2]
				runway_lats += [runway.lat1, runway.lat2]
				runway_hdgs.append(runway.get_heading1_deg())
			
			
			tower_lon, tower_lat = geo.apply_heading_distance(statistics.median(runway_lons), 
																	statistics.median(runway_lats),
																	statistics.median(runway_hdgs) + 90, 50)
			towers[icao] = Tower(tower_lon, tower_lat, 15)
		
		if not parkings[icao]:
			del parkings[icao]
		if not runways[icao]:
			del runways[icao]
		if not ils_d[icao]:
			del ils_d[icao]
		
		i += 1
	print()
	
	if print_runway_lengths:
		print("ICAO	Length	Lon	Lat Tile index")
		for i in sorted(runway_lengths, key=lambda d: d["length-ft"])[:10]:
			print(i["icao"], int(i["length-ft"]), i["lon"], i["lat"], utils.get_fg_tile_index(i["lon"], i["lat"]), sep="\t")
	
	return parkings, taxi_nodes, taxi_edges, towers, runways, ils_d

def find_or_create_pushback_node(taxi_nodes, p):
	pass

def write_groundnet_files(parkings, taxi_nodes, taxi_edges, output, overwrite):
	i = 1
	total = len(parkings)
	for icao in parkings:
		print(f"\rWriting groundnet files … {i / total * 100:.1f}% ({i} of {total})", end="")
		sys.stdout.flush()
		path = os.path.join(output, "Airports", get_icao_xml_path(icao, "groundnet"))
		os.makedirs(os.path.join(*os.path.split(path)[:-1]), exist_ok=True)
		
		if os.path.isfile(path) and not overwrite:
			print(f"\rGroundnet file {path} already exists - skipping, use --overwrite                                             ")
		with open(path, "w") as f:
			utils.files.write_xml_header(f)
			f.write("<groundnet>\n")
			f.write("	<version>1</version>\n")
			f.write("	<parkingList>\n")
			
			for p in parkings[icao]:
				pushback_node = find_or_create_pushback_node(taxi_nodes, p)
				f.write(repr(p))
			
			f.write("	</parkingList>\n")
			f.write("	<TaxiNodes>")
			
			for edge in taxi_edges[icao]:
				taxi_nodes[icao][edge.begin].is_on_runway = edge.is_on_runway
				taxi_nodes[icao][edge.end].is_on_runway = edge.is_on_runway
			
			f.write("</groundnet>\n")
		
		i += 1
	print()

def write_tower_files(towers, output, elevpipe, overwrite):
	i = 1
	total = len(towers)
	for icao in towers:
		print(f"\rWriting tower files … {i / total * 100:.1f}% ({i} of {total})", end="")
		path = os.path.join(output, "Airports", get_icao_xml_path(icao, "twr"))
		os.makedirs(os.path.join(*os.path.split(path)[:-1]), exist_ok=True)
		
		if os.path.isfile(path) and not overwrite:
			print(f"\rTower file {path} already exists - skipping, use --overwrite                                             ")
		with open(path, "w") as f:
			utils.files.write_xml_header(f)
			f.write("<PropertyList>\n")
			f.write(repr(towers[icao]))
			f.write("</PropertyList>\n")
		
		i += 1
	print()

def write_threshold_files(runways, output, overwrite):
	i = 1
	total = len(runways)
	for icao in runways:
		print(f"\rWriting threshold files … {i / total * 100:.1f}% ({i} of {total})", end="")
		sys.stdout.flush()
		path = os.path.join(output, "Airports", get_icao_xml_path(icao, "threshold"))
		os.makedirs(os.path.join(*os.path.split(path)[:-1]), exist_ok=True)
		
		if os.path.isfile(path) and not overwrite:
			print(f"\rThreshold file {path} already exists - skipping, use --overwrite                                             ")
		with open(path, "w") as f:
			utils.files.write_xml_header(f)
			f.write("<PropertyList>\n")
			for runway in runways[icao]:
				f.write(repr(runway))
			f.write("</PropertyList>")
		
		i += 1
	print()

def write_ils_files(ils_d, output, elevpipe, overwrite):
	i = 1
	total = len(ils_d)
	for icao in ils_d:
		print(f"\rWriting ILS files … {i / total * 100:.1f}% ({i} of {total})", end="")
		sys.stdout.flush()
		for ils in ils_d[icao]:
			elevout1, elevout2 = [], []
			if ils.lon1 and ils.lat1:
				elevpipe.stdin.write(f"{icao} {ils.lon1} {ils.lat1}\n".encode("utf-8"))
				elevpipe.stdin.flush()
				elevout1 = elevpipe.stdout.readline().split()
				if len(elevout1) == 2:
					ils.elev1 = float(elevout1[1])
			
			if ils.lon2 and ils.lat2:
				elevpipe.stdin.write(f"{icao} {ils.lon2} {ils.lat2}\n".encode("utf-8"))
				elevpipe.stdin.flush()
				elevout2 = elevpipe.stdout.readline().split()
				if len(elevout2) == 2:
					ils.elev2 = float(elevout2[1])
			
			if not len(elevout1) == 2 and len(elevout2) == 2:
				continue
		
		if not list(filter(None, ils_d[icao])):
			continue
		
		path = os.path.join(output, "Airports", get_icao_xml_path(icao, "ils"))
		os.makedirs(os.path.join(*os.path.split(path)[:-1]), exist_ok=True)
		
		if os.path.isfile(path) and not overwrite:
			print(f"\rILS file {path} already exists - skipping, use --overwrite                                             ")
		with open(path, "w") as f:
			utils.files.write_xml_header(f)
			f.write("<PropertyList>\n")
			for ils in ils_d[icao]:
				if ils:
					f.write(repr(ils))
			f.write("</PropertyList>\n")
		
		i += 1
	print()
	print(i)

if __name__ == "__main__":
	argp = argparse.ArgumentParser(description="Convert apt.dat files to groundnet.xml files")
	
	argp.add_argument(
		"-i", "--input",
		help="Input apt.dat file(s) or folder(s) containing such files",
		required=True,
		nargs="+"
	)
	
	argp.add_argument(
		"-o", "--output",
		help="Folder to put Airports/I/C/A/ICAO.groundnet.xml into",
		required=True
	)
	
	argp.add_argument(
		"--overwrite",
		help="Whether to overwrite already existing files (default: False)",
		action="store_true"
	)
	
	argp.add_argument(
		"-n", "--nav-dat",
		help="Path to nav.dat file",
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
		"-p", "--print-runway-lengths",
		help="Only print runway lengths, do not write any files",
		action="store_true"
	)
	
	args = argp.parse_args()
	
	print("Searching apt.dat files … ", end="")
	files = find_input_files(args.input, suffix=".dat")
	print(f"done, found {len(files)} files")
	parkings, taxi_nodes, taxi_edges, towers, runways, ils_d = parse_aptdat_files(files, args.nav_dat, args.print_runway_lengths)
	
	if not args.print_runway_lengths:
		elevpipe = utils.make_fgelev_pipe(args.fgelev, args.fgscenery, args.fgdata)
		write_groundnet_files(parkings, taxi_nodes, taxi_edges, args.output, args.overwrite)
		write_tower_files(towers, args.output, elevpipe, args.overwrite)
		write_threshold_files(runways, args.output, args.overwrite)
		write_ils_files(ils_d, args.output, elevpipe, args.overwrite)


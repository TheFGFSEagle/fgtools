#!/usr/bin/env python
#-*- coding:utf-8 -*-

import logging
import os

from plum import dispatch

from fgtools.utils import files
from fgtools import geo
from fgtools.utils import unit_convert
from fgtools import utils
from fgtools.geo.rectangle import Rectangle

class Code:
	def __init__(self, name, code):
		self.name = name
		self.code = code
	
	def __str__(self):
		return self.name
	
	def __repr__(self):
		return str(self.code)
	
	def __int__(self):
		return self.code
	
	def __float__(self):
		return float(self.code)
	
	def __eq__(self, other):
		if isinstance(other, Code):
			return self.name == other.name
		elif isinstance(other, str):
			return self.name == other
		elif isinstance(other, int):
			return self.code == other
	
	def __ne__(self, other):
		if isinstance(other, Code):
			return self.name != other.name
		elif isinstance(other, str):
			return self.name != other
		elif isinstance(other, int):
			return self.code != other

class CodeEnum:
	def __init__(self, names, codes):
		self._codemap = {}
		for name, code in zip(names, codes):
			codeobject = Code(name, code)
			setattr(self, name, codeobject)
			self._codemap[code] = codeobject
	
	def __getitem__(self, key):
		return self._codemap[key]

SurfaceCode = CodeEnum(
	("Asphalt", "Concrete", "Grass", "Dirt", "Gravel", "DryLakebed", "Water", "SnowIce", "Transparent"),
	list(range(1, 6)) + list(range(12, 16))
)

RunwayShoulderCode = CodeEnum(
	("NoShoulder", "Asphalt", "Concrete"),
	range(3)
)

RunwayMarkingCode = CodeEnum(
	("NoMarkings", "Visual", "NonPrecision", "Precision", "UKNonPrecision", "UKPrecision"),
	range(6)
)

ApproachLightsCode = CodeEnum(
	("NoLights", "ALSF_I", "ALSF_II", "Calvert", "CalvertILS", "SSALR", "SSALF", "SALS", "MALSR", "MALSF", "MALS", "ODALS", "RAIL"),
	range(13)
)

LineTypeCode = CodeEnum(
	(
		"NoLine", "TaxiwayCenter", "MiscBoundary", "TaxiwayEdge", "RunwayHold", "OtherHold", "ILSHold",
		"TaxiwayCenterRunwaySafety", "AircraftQueueLane", "AircraftQueueLaneDouble",
		"TaxiwayCenterLarge", "TaxiwayCenterRunwaySafetyLarge", "RunwayHoldLarge", "OtherHoldLarge", "ILSHoldLarge",
		"TaxiwayCenterBordered", "MiscBoundaryBordered", "TaxiwayEdgeBordered", "RunwayHoldBordered",
		"OtherHoldBordered", "ILSHoldBordered", "TaxiwayCenterRunwaySafetyBordered", "AircraftQueueLaneBordered",
		"AircraftQueueLaneDoubleBordered", "TaxiwayCenterLargeBordered", "TaxiwayCenterRunwaySafetyLargeBordered",
		"RunwayHoldLargeBordered", "OtherHoldLargeBordered", "ILSHoldLargeBordered",
		"TaxiwayShoulder", "RoadwayEdge", "RoadwayEdgeAircraftMovingArea", "RoadwayCenter", "RoadwayEdgeBroken",
		"RoadwayEdgeWide", "RoadwayCenterWide", "SolidRed", "DashedRed", "SolidRedWide", "SolidOrange",
		"SolidBlue", "SolidGreen", "RoadwayEdgeBordered", "RoadwayEdgeAircraftMovingAreaBordered",
		"RoadwayCenterBordered", "RoadwayEdgeBrokenBordered", "RoadwayEdgeWideBordered",
		"RoadwayCenterWideBordered", "SolidRedBordered", "DashedRedBordered", "SolidRedWideBordered",
		"SolidOrangeBordered", "SolidBlueBordered", "SolidGreenBordered"
	),
	tuple(range(15)) + tuple(range(51, 65)) + tuple(range(19, 26)) + (30, 31, 32) + (40, 41, 42) + \
		tuple(range(70, 76)) + (80, 81, 82) + (90, 91, 92)
)

LineLightTypeCode = CodeEnum(
	(
		"TaxiwayCenter", "TaxiwayEdge", "Hold", "RunwayHold", "TaxiwayCenterRunwaySafety",
		"TaxiwayEdgeDangerous", "TaxiwayLeadOff", "TaxiwayLeadOffAmber"
	),
	range(101, 109)
)

BeaconTypeCode = CodeEnum(
	("NoBeacon", "CivilianAirport", "Seaport", "Heliport", "MilitaryAirport"),
	range(5)
)

SignSizeCode = CodeEnum(
	("TaxiwaySmall", "TaxiwayMedium", "TaxiwayLarge", "DistanceRemainingLarge", "DistanceRemainingSmall"),
	range(1, 6)
)

LightingObjectCode = CodeEnum(
	("VASI", "PAPI4L", "PAPI4R", "PAPISpaceShuttle", "TriColorVASI", "RunwayGuard"),
	range(1, 7)
)

REILCode = CodeEnum(
	("NoREIL", "OmnidirREIL", "UnidirREIL"),
	range(3)
)

AirportType = CodeEnum(
	("Land", "Sea", "Heli"),
	(1, 16, 17)
)

class Object:
	def __init__(self):
		pass
	
	def read(self, line):
		pass
	
	def write(self, f):
		if None in vars(self).values():
			raise RuntimeError("object fields " + list(filter(lambda item: item[1] == None, vars(self).items())) + " are uninitialized")

class Helipad(Object):
	@dispatch
	def __init__(self, id, lon, lat, heading, length, width, surface, markings=0, shoulder=RunwayShoulderCode.NoShoulder,
				smoothness=0.25, edge_lights=False):
		Object.__init__(self)
		self.id = id
		self.lon = lon
		self.lat = lat
		self.heading = heading
		self.length = length
		self.width = width
		self.surface = surface
		self.markings = markings
		self.shoulder = shoulder
		self.smoothness = smoothness
		self.edge_lights = edge_lights
	
	@dispatch
	def __init__(self):
		Object.__init__(self)
		self.id = self.lon = self.lat = self.heading = self.length = self.width = self.surface = self.markings = self.shoulder = self.smoothness = self.edge_lights = None
	
	def read(self, line):
		Object.read(self, line)
		print(line)
		self.id, self.lat, self.lon, self.heading, self.length, self.width, self.surface, self.markings, self.shoulder, self.smoothness, self.edge_lights = \
						line[1], float(line[2]), float(line[3]), float(line[4]), float(line[5]), float(line[6]), SurfaceCode[int(line[7])], \
						int(line[8]), RunwayShoulderCode[int(line[9])], float(line[10]), bool(int(line[11]))
	
	def write(self, f):
		Object.write(self. f)
		f.write((f"102 {self.id} {float(self.lat)} {float(self.lon)} {float(self.heading)} {float(self.length):.2f}" +
				f" {float(self.width):.2f} {int(self.surface)} {int(self.markings)} {int(self.shoulder)} {float(self.smoothness):.2f} {int(self.edge_lights)}\n"))

class Runway:
	@dispatch
	def __init__(self, width, id1, lon1, lat1, id2, lon2, lat2):
		Object.__init__(self)
		self.width = width
		self.id1 = id1
		self.lon1 = lon1
		self.lat1 = lat1
		self.id2 = id2
		self.lon2 = lon2
		self.lat2 = lat2
	
	@dispatch
	def __init__(self):
		Object.__init__(self)
		self.id = self.lon = self.lat = self.heading = self.length = self.width = self.surface = self.shoulder = self.smoothness = self.edge_lights = None
	
	def get_heading1(self):
		return geo.get_bearing_deg(self.lon1, self.lat1, self.lon2, self.lat2)
	
	def get_heading2(self):
		return utils.wrap_period(self.get_heading1() + 180, 0, 360)
	
	def get_length_m(self):
		return geo.great_circle_distance_m(self.lon1, self.lat1, self.lon2, self.lat2)
	
	def get_length_ft(self):
		return unit_convert.m2ft(self.get_length_m())
	
	def read(self, line):
		Object.read(self, line)
	
	def write(self, f):
		Object.write(self. f)

class WaterRunway(Runway):
	@dispatch
	def __init__(self, width, id1, lon1, lat1, id2, lon2, lat2, perimeter_buoys=False):
		Runway.__init__(self, width, id1, lon1, lat1, id2, lon2, lat2)
		
		self.perimeter_buoys = perimeter_buoys
	
	@dispatch
	def __init__(self):
		Runway.__init__(self, None, None, None, None, None, None, None)
	
	def read(self, line):
		Runway.read(self, line)
		self.width, self.perimeter_buoys, self.id1, self.lat1, self.lon1, self.id2, self.lat2, self.lon2 = \
						float(line[1]), bool(int(line[2])), line[3], float(line[4]), float(line[5]), line[6], float(line[7]), float(line[8])
	
	def write(self, f):
		Runway.write(self, f)
		f.write((f"101 {float(self.width):.2f} {int(self.perimeter_buoys)} {self.id1} {float(self.lat1):.8f}" + 
				f" {float(self.lon1):.8f} {self.id2} {float(self.lat2):.8f} {float(self.lon2):.8f}\n"))

class LandRunway(Runway):
	@dispatch
	def __init__(self, width, surface, id1, lon1, lat1, id2, lon2, lat2, 
						smoothness=0.25, shoulder=RunwayShoulderCode.NoShoulder, center_lights=False,
						edge_lights=False, distance_signs=False,
						displ_thresh1=0, blastpad1=0, markings1=RunwayMarkingCode.Visual,
						appr_lights1=ApproachLightsCode.NoLights, tdz_lights1=False, reil_type1=REILCode.NoREIL,
						displ_thresh2=0, blastpad2=0, markings2=RunwayMarkingCode.Visual,
						appr_lights2=ApproachLightsCode.NoLights, tdz_lights2=False, reil_type2=REILCode.NoREIL):
		Runway.__init__(self, width, id1, lon1, lat1, id2, lon2, lat2)
		
		self.surface = surface
		self.shoulder = shoulder
		self.smoothness = smoothness
		self.center_lights = center_lights
		self.edge_lights = edge_lights
		self.distance_signs = distance_signs
		
		self.displ_thresh1 = displ_thresh1
		self.blastpad1 = blastpad1
		self.markings1 = markings1
		self.appr_lights1 = appr_lights1
		self.tdz_lights1 = tdz_lights1
		self.reil_type1 = reil_type1
		
		self.displ_thresh2 = displ_thresh2
		self.blastpad2 = blastpad2
		self.markings2 = markings2
		self.appr_lights2 = appr_lights2
		self.tdz_lights2 = tdz_lights2
		self.reil_type2 = reil_type2
	
	@dispatch
	def __init__(self):
		Runway.__init__(self, None, None, None, None, None, None, None,)
		self.surface = self.shoulder = self.smoothness = self.center_lights = self.edge_lights = self.distance_signs = \
			self.displ_thresh1 = self.blastpad1 = self.markings1 = self.appr_lights1 = self.tdz_lights1 = self.reil_type1 = \
			self.displ_thresh2 = self.blastpad2 = self.markings2 = self.appr_lights2 = self.tdz_lights2 = self.reil_type2 = None
	
	def read(self, line):
		Runway.read(self, line)
		self.width, self.surface, self.shoulder, self.smoothness, self.center_lights, self.edge_lights, self.distance_signs, \
			self.id1, self.lat1, self.lon1, self.displ_thresh1, self.blastpad1, \
			self.markings1, self.appr_lights1, self.tdz_lights1, self.reil_type1, \
			self.id2, self.lat2, self.lon2, self.displ_thresh2, self.blastpad2, \
			self.markings2, self.appr_lights2, self.tdz_lights2, self.reil_type2 = \
						float(line[1]), SurfaceCode[int(line[2])], RunwayShoulderCode[int(line[3])], float(line[4]), \
						bool(int(line[5])), bool(int(line[6])), bool(int(line[7])), \
						line[8], float(line[9]), float(line[10]), float(line[11]), float(line[12]), \
						RunwayMarkingCode[int(line[13])], ApproachLightsCode[int(line[14])], bool(int(line[15])), REILCode[int(line[16])], \
						line[17], float(line[18]), float(line[19]), float(line[20]), float(line[21]), \
						RunwayMarkingCode[int(line[22])], ApproachLightsCode[int(line[23])], bool(int(line[24])), REILCode[int(line[25])]
	
	def write(self, f):
		Runway.write(self, f)
		f.write((f"100 {float(self.width):.2f} {int(self.surface)} {int(self.shoulder)} {float(self.smoothness)} {int(self.center_lights)}" +
				f" {int(self.edge_lights)} {int(self.distance_signs)}" + 
				f" {self.id1} {float(self.lat1):.8f} {float(self.lon1):.8f} {float(self.displ_thresh1):.2f} {float(self.blastpad1):.2f} {int(self.markings1)}" + 
				f" {int(self.appr_lights1)} {int(self.tdz_lights1)} {int(self.reil_type1)}" + 
				f" {self.id2} {float(self.lat2):.8f} {float(self.lon2):.8f} {float(self.displ_thresh2):.2f} {float(self.blastpad2):.2f} {int(self.markings2)}" + 
				f" {int(self.appr_lights2)} {int(self.tdz_lights2)} {int(self.reil_type2)}\n"))

class Metadata(Object):
	@dispatch
	def __init__(self, key, value):
		Object.__init__(self)
		
		self.key = key
		self.value = value
	
	@dispatch
	def __init__(self):
		Object.__init__(self)
		self.key = self.value = None
	
	def read(self, line):
		Object.read(self, line)
		self.key, self.value = line[1], " ".join(line[2:])
	
	def write(self, f):
		Object.write(self, f)
		f.write(f"1302 {key} {value}\n")

class Airport:
	@dispatch
	def __init__(self, elev, icao, name, bbox, lon, lat, type=AirportType.Land):
		self.metadata = {}
		self.runways = {}
		self.helipads = {}
		self.parkings = []
		self.aprons = []
		self.tower = None
		self.windsocks = []
		self.beacons = []
		
		self.elev = elev
		self.icao = icao
		self.name = name
		self.type = type
		self.bbox = bbox
		self.lon = lon
		self.lat = lat
	
	@dispatch
	def __init__(self):
		self.metadata = {}
		self.runways = {}
		self.helipads = {}
		self.parkings = []
		self.aprons = []
		self.tower = None
		self.windsocks = []
		self.beacons = []
		
		self.elev = self.icao = self.type = self.bbox = self.lon = self.lat = None
	
	def __repr__(self):
		return f"Airport(elev={self.elev}, icao={self.icao}, type={self.type}, bbox={self.bbox})"
	
	def add_runway(self, runway):
		self.runways[runway.id1] = runway
	
	def add_helipad(self, helipad):
		self.helipads[helipad.id] = helipad
	
	def read(self, f):
		line = ""
		while line := f.readline():
			line = line.strip()
			if line:
				break
		else:
			return
		line = line.split()
		self.type, self.elev, _, _, self.icao = AirportType[int(line[0])], float(line[1]), line[2], line[3], line[4]
		if len(line) > 5:
			self.name = " ".join(line[5])
		else:
			self.name = ""
		
		rowcode = -1
		line = ""
		last_line_start = 0
		while line := f.readline():
			if line.strip() == "":
				continue
			line = line.split()
			
			rowcode = int(line[0])
			if rowcode in (1, 16, 17):
				f.seek(last_line_start)
				break
			
			if rowcode == 100:
				obj = LandRunway()
				obj.read(line)
				self.add_runway(obj)
			elif rowcode == 101:
				obj = WaterRunway()
				obj.read(line)
				self.add_runway(obj)
			elif rowcode == 102:
				obj = Helipad()
				obj.read(line)
				self.add_helipad(obj)
			elif rowcode == 1302:
				obj = Metadata()
				obj.read(line)
				self.metadata[obj.key] = obj
			
			last_line_start = f.tell()
		
		runway_lons = list(map(lambda id: self.runways[id].lon1, self.runways)) + list(map(lambda id: self.runways[id].lon2, self.runways))
		runway_lats = list(map(lambda id: self.runways[id].lat1, self.runways)) + list(map(lambda id: self.runways[id].lat2, self.runways))
		self.bbox = Rectangle((float(min(runway_lons)), float(min(runway_lats))), (float(max(runway_lons)), float(max(runway_lats))))
		
		if "datum_lon" in self.metadata and "datum_lat" in self.metadata:
			self.lon = float(self.metadata["datum_lon"].value)
			self.lat = float(self.metadata["datum_lat"].value)
		else:
			self.lon = self.bbox.midpoint().lon
			self.lat = self.bbox.midpoint().lat
		
	def write(self, f):
		if None in (self.elev, self.icao, self.name, self.type, self.lon, self.lat):
			raise RuntimeError("object fields " + list(filter(lambda item: item[1] == None, vars(self).items())) + " are uninitialized")
		f.write(f"{repr(self.type)} {float(self.elev):.2f} 0 0 {self.icao} {self.name}\n")
		
		for metadata in self.metadata:
			metadata.write(f)
		
		for id in self.runways:
			self.runways[id].write(f)
		for id in self.helipads:
			self.helipads[id].write(f)
		for parking in self.parkings:
			parking.write(f)
		for apron in self.aprons:
			apron.write(f)
		if self._tower:
			self.tower.write(f)
		for windsock in self.windsocks:
			windsock.write(f)
		for beacon in self.beacons:
			beacon.write(f)

class ReaderWriterAptDat:
	def __init__(self, file_header="Generated by fgtools.aptdat.ReaderWriterAptDat"):
		self._airports = []
		self.file_header = file_header
	
	def _get_airport_index(self, icao):
		for i, airport in enumerate(self._airports):
			if airport.icao == icao:
				return i
		return -1
	
	def add_airport(self, airport):
		if not airport in self._airports:
			self._airports.append(airport)
	
	def add_airports(self, airports):
		for airport in airports:
			self.add_airport(airport)
	
	def get_airport(self, icao):
		i = _get_airport_index(icao)
		if i > -1:
			return self._airports[i]
	
	def get_airports(self, icaos=None):
		if icaos == None:
			return self._airports
		
		l = []
		for icao in icaos:
			l.append(self.get_airport(icao))
		return l
	
	def set_airport(self, airport):
		i = self._get_airport_index(airport.icao)
		if i > -1:
			self._airports[i] = airport
		else:
			self.add_airport(airport)
		return i
	
	def set_airports(self, airports):
		for airport in airports:
			self.set_airport(airport)
	
	def remove_airport(self, icao):
		return self._airports.pop(self._get_airport_index(icao))
	
	def remove_airports(self, icaos=None):
		if icaos == None:
			self._airports = []
		for icao in icaos:
			yield self._airports.pop(self._get_airport_index(icao))
	
	def read(self, path):
		exists = files.check_exists(path, exit=False)
		if exists == 1:
			pass
		elif exists == 2:
			self.read_multiple(os.listdir(path))
		else:
			logging.fatal(f"Path {path} does not exist - exiting !")
		
		with open(path, "r") as f:
			f.seek(0, 2)
			file_size = f.tell()
			f.seek(0)
			
			f.readline()
			f.readline()
			
			while f.tell() != file_size:
				airport = Airport()
				airport.read(f)
				self.add_airport(airport)
	
	def read_multiple(self, paths):
		for path in paths:
			self.read(path)
	
	# Write apt.dat files into output
	# @param output -> str 				Path to put apt.dat files into
	# @param merge -> bool 			Whether to merge all airports into one apt.dat file or write one file per airport
	# @param overwrite -> bool 		Whether to overwrite an apt.dat file when it already exists
	# @param overwrite_func -> callable Function whose return value replces overwrite - will get passed
	#									output_path as positional argument, will be called only if path actually
	#									exists and is a file
	# @return bool 						0 on success, 1 if the apt.dat file already exists and overwrite == False
	def write(self, output, merge=False, overwrite=False, overwrite_func=None):
		if len(self._airports) == 0:
			print("ReaderWriterAptDat has no airports - not writing anything !")
			return 1
		if merge:
			exists = files.check_exists(output, type="file", exit=False)
			if exists == 2:
				output = os.path.join(output, "apt.dat")
			
			exists = files.check_exists(output, type="file", exit=False)
			if exists == 1:
				if callable(overwrite_func):
					overwrite = overwrite_func(path)
					if not overwrite:
						print(f"Output file {output} exists already - not writing any airports !")
						return 1
			elif exists == 2:
				print(f"Output path {path} for airport is a directory - skipping", end=" " * 100 + "\n")
				return 1
			
			with open(output, "w") as f:
				self._write_header(f)
				i = 0
				total = len(airports)
				for airport in self._airports:
					print(f"Writing airports … {i / total * 100}% ({i} of {total} airports done)", end="\r")
					i += 1
					airport.write(f)
				print(f"Writing airports … {i / total * 100}% ({i} of {total} airports done)")
				self._write_footer(f)
		else:
			files.check_exists(output, type="dir")
			i = 0
			total = len(self._airports)
			skipped = 0
			for airport in self._airports:
				print(f"Writing airports … {i / total * 100}% ({i} of {total} airports done, {skipped} skipped)", end="\r")
				i += 1
				path = os.path.join(output, airport.icao + ".dat")
				exists = files.check_exists(path, type="file", exit=False, create=True)
				if exists == 1:
					if callable(overwrite_func):
						overwrite = overwrite_func(path)
					if not overwrite:
						print(f"Output file {path} for airport exists already - skipping", end=" " * 100 + "\n")
						skipped += 1
						continue
				elif exists == 2:
					print(f"Output path {path} for airport is a directory - skipping", end=" " * 100 + "\n")
					continue
				with open(path, "w") as f:
					self._write_header(f)
					airport.write(f)
					self._write_footer(f)
			print(f"Writing airports … {i / total * 100}% ({i} of {total} airports done, {skipped} skipped)", end=" " * 100 + "\n")
		return 0
	
	def _write_header(self, f):
		f.write("I\n")
		f.write(f"1130 {self.file_header}\n")
	
	def _write_footer(self, f):
		f.write("99\n")

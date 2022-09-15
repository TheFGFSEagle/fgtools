#!/usr/bin/env python
#-*- coding:utf-8 -*-

import logging
import os

from fgtools.utils import files
from fgtools import geo
from fgtools.utils import unit_convert
from fgtools import utils

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
		for name, code in zip(names, codes):
			setattr(self, name, Code(name, code))
		
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

class Helipad:
	def __init__(self, id, lon, lat, heading, length, width, surface, shoulder=RunwayShoulderCode.NoShoulder,
				smoothness=0.25, edge_lights=False):
		self.id = id
		self.lon = lon
		self.lat = lat
		self.heading = heading
		self.length = length
		self.width = width
		self.surface = surface
		self.shoulder = shoulder
		self.smoothness = smoothness
		self.edge_lights = edge_lights
	
	def write(self, f):
		f.write((f"102 {self.id} {float(self.lat)} {float(self.lon)} {float(self.heading)} {float(self.length):.2f}" +
				f" {float(self.width):.2f} {int(self.surface)} {int(self.shoulder)} {float(self.smoothness):.2f} {int(self.edge_lights)}\n"))

class Runway:
	def __init__(self, width, id1, lon1, lat1, id2, lon2, lat2):
		self.width = width
		self.id1 = id1
		self.lon1 = lon1
		self.lat1 = lat1
		self.id2 = id2
		self.lon2 = lon2
		self.lat2 = lat2
	
	def get_heading1(self):
		return geo.get_bearing_deg(self.lon1, self.lat1, self.lon2, self.lat2)
	
	def get_heading2(self):
		return utils.wrap_period(self.get_heading1() + 180, 0, 360)
	
	def get_length_m(self):
		return geo.great_circle_distance_m(self.lon1, self.lat1, self.lon2, self.lat2)
	
	def get_length_ft(self):
		return unit_convert.m2ft(self.get_length_m())

class WaterRunway(Runway):
	def __init__(self, width, id1, lon1, lat1, id2, lon2, lat2, perimeter_buoys=False):
		Runway.__init__(self, width, id1, lon1, lat1, id2, lon2, lat2)
		
		self.perimeter_buoys = perimeter_buoys
	
	def write(self, f):
		f.write((f"101 {float(self.width):.2f} {int(self.perimeter_buoys)} {self.id1} {float(self.lat1):.8f}" + 
				f" {float(self.lon1):.8f} {self.id2} {float(self.lat2):.8f} {float(self.lon2):.8f}\n"))

class LandRunway(Runway):
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
	
	def write(self, f):
		f.write((f"100 {float(self.width):.2f} {int(self.surface)} {int(self.shoulder)} {self.smoothness} {int(self.center_lights)}" +
				f" {int(self.edge_lights)} {int(self.distance_signs)}" + 
				f" {self.id1} {float(self.lat1):.8f} {float(self.lon1):.8f} {float(self.displ_thresh1):.2f} {float(self.blastpad1):.2f} {int(self.markings1)}" + 
				f" {int(self.appr_lights2)} {int(self.tdz_lights2)} {int(self.reil_type2)}" + 
				f" {self.id2} {float(self.lat2):.8f} {float(self.lon2):.8f} {float(self.displ_thresh2):.2f} {float(self.blastpad2):.2f} {int(self.markings2)}" + 
				f" {int(self.appr_lights2)} {int(self.tdz_lights2)} {int(self.reil_type2)}\n"))

class Airport:
	def __init__(self, elev, icao, name, lon, lat, type=AirportType.Land):
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
		self.lon = lon
		self.lat = lat
	
	def add_runway(self, runway):
		self.runways[runway.id1] = runway
	
	def add_helipad(self, helipad):
		self.helipads[helipad.id] = helipad
	
	def write(self, f):
		f.write(f"{repr(self.type)} {int(self.elev)} 0 0 {self.icao} {self.name}\n")
		f.write(f"1302 datum_lat {self.lat}\n")
		f.write(f"1302 datum_lon {self.lon}\n")
		f.write(f"1302 icao_code {self.icao}\n")
		for id in self.runways:
			self.runways[id].write(f)
		for id in self.helipads:
			self.helipads[id].write(f)
		"""for parking in self.parkings:
			parking.write(f)
		for apron in self.aprons:
			apron.write(f)
		if self._tower:
			self.tower.write(f)
		for windsock in self.windsocks:
			windsock.write(f)
		for beacon in self.beacons:
			beacon.write(f)"""

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
	
	def get_airports(self, icaos):
		for icao in icaos:
			yield self.get_airport(icao)
	
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
	
	def remove_airports(self, icaos):
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

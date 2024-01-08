#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import argparse
import requests
import subprocess
import typing
import json
import zipfile
import shutil
import logging
import tqdm
if sys.version_info[0:2] >= (3, 9):
	from importlib.resources import files as importlib_resources_files
else:
	from importlib_resources import files as importlib_resources_files

import shapely.geometry

from fgtools.geo import Rectangle, Coord, get_fg_tile_coords, get_fg_tile_span, get_fg_tile_indices, get_fg_tile_paths, FG_TILE_HEIGHT
from fgtools import aptdat, get_logger
from fgtools.utils.files import find_input_files, get_cached_file, get_newest_mtime
from fgtools.utils import padded_print, read_timestamp, write_timestamp, format_size, download, run_command, quote

GEOFABRIK_REGIONS = {
	"africa": [
		'algeria', 'angola', 'benin', 'botswana', 'burkina-faso', 'burundi', 'cameroon',
		'canary-islands', 'cape-verde', 'central-african-republic', 'chad', 'comores',
		'congo-brazzaville', 'congo-democratic-republic', 'djibouti',
		'egypt', 'equatorial-guinea', 'eritrea', 'ethiopia', 'gabon', 'ghana', 'guinea',
		'guinea-bissau', 'ivory-coast', 'kenya', 'lesotho', 'liberia', 'libya', 'madagascar',
		'malawi', 'mali', 'mauritania', 'mauritius', 'morocco', 'mozambique', 'namibia',
		'niger', 'nigeria', 'rwanda', 'saint-helena-ascension-and-tristan-da-cunha',
		'sao-tome-and-principe', 'senegal-and-gambia', 'seychelles', 'sierra-leone', 'somalia',
		'south-africa', 'south-sudan', 'sudan', 'swaziland', 'tanzania', 'togo', 'tunisia',
		'uganda', 'zambia', 'zimbabwe'
	],
	"antarctica": {},
	"asia": [
		'afghanistan', 'armenia', 'azerbaijan', 'bangladesh', 'bhutan', 'cambodia', 'china', 'east-timor',
		'gcc-states', 'india', 'indonesia', 'iran', 'iraq', 'israel-and-palestine', 'japan',
		'jordan', 'kazakhstan', 'kyrgyzstan', 'laos', 'lebanon', 'malaysia-singapore-brunei', 'maldives',
		'mongolia', 'myanmar', 'nepal', 'north-korea', 'pakistan', 'philippines',
		'south-korea', 'sri-lanka', 'syria', 'taiwan', 'tajikistan', 'thailand',
		'turkmenistan', 'uzbekistan', 'vietnam', 'yemen'
	],
	"australia-oceania": [
		'american-oceania', 'australia', 'cook-islands', 'fiji', 'ile-de-clipperton', 'kiribati', 'marshall-islands',
		'micronesia', 'nauru', 'new-caledonia', 'new-zealand', 'niue', 'palau', 'papua-new-guinea',
		'pitcairn-islands', 'polynesie-francaise', 'samoa', 'solomon-islands', 'tokelau', 'tonga', 'tuvalu',
		'vanuatu', 'wallis-et-futuna'
	],
	"central-america": [
		'bahamas', 'belize', 'costa-rica', 'cuba', 'el-salvador', 'guatemala', 'haiti-and-domrep',
		'honduras', 'jamaica', 'nicaragua', 'panama'
	],
	"europe": [
		'albania', 'andorra', 'austria', 'azores', 'belarus', 'belgium', 'bosnia-herzegovina', 'bulgaria',
		'croatia', 'cyprus', 'czech-republic', 'denmark', 'estonia', 'faroe-islands', 'finland', 'france', 'georgia',
		'germany', 'great-britain', 'greece', 'guernsey-jersey', 'hungary', 'iceland', 'ireland-and-northern-ireland',
		'isle-of-man', 'italy', 'kosovo', 'latvia', 'liechtenstein', 'lithuania', 'luxembourg', 'macedonia', 'malta',
		'moldova', 'monaco', 'montenegro', 'netherlands', 'norway', 'poland', 'portugal', 'romania',
		'serbia', 'slovakia', 'slovenia', 'spain', 'sweden', 'switzerland', 'turkey', 'ukraine'
	],
	"north-america": [
		'canada', 'greenland', 'mexico', 'us'
	],
	"russia": [],
	"south-america": [
		'argentina', 'bolivia', 'brazil', 'chile', 'colombia', 'ecuador', 'guyana', 'paraguay', 'peru',
		'suriname', 'uruguay', 'venezuela'
	]
}

GEOFABRIK_DOWNLOAD_URL = "http://download.geofabrik.de/"
DEMSEARCH_URL = "http://www.imagico.de/map/dem_json.php?date=&lon={lon_ll}&lat={lat_ll}&lonE={lon_ur}&latE={lat_ur}&srtm=0&glcf1=0&glcf2=0&glcf3=0&glcf4=0&gls=0&cgiar=0&vf=1&aster=0&ca=0&ca2=0&ned1=0&ned3=0&ned2=0&srtm1=0&srtm1o=0"

class OsmSelector:
	def __init__(self, selector, material):
		self.selector = selector
		self.material = material

class OsmSelectorPolygon(OsmSelector):
	def __init__(self, selector, material):
		OsmSelector.__init__(self, selector, material)

class OsmSelectorLine(OsmSelector):
	def __init__(self, selector, material, line_width):
		OsmSelector.__init__(self, selector, material)
		self.line_width = line_width

class OsmSelectorPoint(OsmSelector):
	def __init__(self, selector, material, point_width):
		OsmSelector.__init__(self, selector, material)
		self.point_width = point_width


OSM_MATERIAL_MAPPINGS = [
	OsmSelectorPolygon("landuse in ('cemetery')", "Cemetery"),
	OsmSelectorPolygon("landuse in ('park', 'meadow', 'allotments', 'recreation_ground', 'grass', 'greenfield') or military = 'training_area' or leisure in ('recreation_ground', 'nature_reserve', 'park', 'common') or landcover = 'grass'", "GrassCover"),
	OsmSelectorPolygon("landuse in ('industrial')", "Industrial"),
	OsmSelectorPolygon("landuse in ('farmland', 'plant_nursery')", "MixedCrop"),
	OsmSelectorPolygon("(landuse in ('forest') or natural in ('wood') or landcover = 'trees' or boundary in ('national_park')) and leaf_cyle in ('', 'mixed')", "MixedForest"),
	OsmSelectorPolygon("(landuse in ('forest') or natural in ('wood') or landcover = 'trees' or boundary in ('national_park')) and leaf_cyle = 'evergreen'", "EvergreenForest"),
	OsmSelectorPolygon("(landuse in ('forest') or natural in ('wood') or landcover = 'trees' or boundary in ('national_park')) and leaf_cyle in ('deciduous', 'semi_deciduous')", "DeciduousForest"),
	OsmSelectorPolygon("(landuse in ('forest') or natural in ('wood') or landcover = 'trees' or boundary in ('national_park')) and leaf_cyle = 'semi_evergreen'", "RainForest"),
	OsmSelectorPolygon("(landuse in ('forest') or natural in ('wood') or landcover = 'trees' or boundary in ('national_park')) and leaf_cyle = 'evergreen'", "EvergreenForest"),
	OsmSelectorPolygon("landuse in ('quarry')", "OpenMining"),
	OsmSelectorPolygon("landuse in ('farmyard')", "Sand"),
	OsmSelectorPolygon("landuse in ('scrub')", "Scrub"),
	OsmSelectorPolygon("landuse in ('commercial', 'retail')", "SubUrban"),
	OsmSelectorPolygon("landuse in ('residential')", "Town"),
	OsmSelectorPolygon("landuse in ('vineyard')", "Vineyard"),
	OsmSelectorPolygon("landuse in ('construction')", "Construction"),
	OsmSelectorPolygon("landuse in ('landfill')", "Dump"),
	OsmSelectorPolygon("landuse in ('brownfield')", "Dirt"),
	OsmSelectorPolygon("landuse in ('salt_pond')", "Saline"),
	OsmSelectorPolygon("natural in ('heath')", "Heath"),
	OsmSelectorPolygon("natural in ('beach', 'shingle', 'dune')", "Sand"),
	OsmSelectorPolygon("natural in ('glacier')", "Glacier"),
	OsmSelectorPolygon("natural in ('mine')", "OpenMining"),
	OsmSelectorPolygon("natural in ('cliff', 'bare_rock', 'rock', 'scree')", "Rock"),
	OsmSelectorPolygon("((natural = 'water' and water = '') or water in ('lake', 'oxbow')) and (intermittent = 'no' and seasonal is NULL)", "Lake"),
	OsmSelectorPolygon("((natural = 'water' and water = '') or water in ('lake', 'oxbow')) and (intermittent = 'yes' or seasonal is not NULL)", "IntermittentLake"),
	OsmSelectorPolygon("natural = 'volcano'", "Lava"),
	OsmSelectorPolygon("natural = 'scrub'", "Scrub"),
	OsmSelectorPolygon("natural = 'fell'", "ShrubGrassCover"),
	OsmSelectorPolygon("natural = 'tundra'", "HerbTundra"),
	OsmSelectorPolygon("natural = 'mud'", "Marsh"),
	OsmSelectorPolygon("natural = 'wetland'", "FloodLand"),
	OsmSelectorPolygon("wetland = 'marsh'", "Marsh"),
	OsmSelectorPolygon("wetland = 'saltmarsh'", "SaltMarsh"),
	OsmSelectorPolygon("wetland = 'tidalflat'", "Tidal"),
	OsmSelectorPolygon("wetland = 'mangrove'", "Mangrove"),
	OsmSelectorPolygon("wetland = 'bog'", "Bog"),
	OsmSelectorPolygon("water = 'river' or waterway = 'riverbank'", "River"),
	OsmSelectorPolygon("water in ('lock', 'moat', 'reflecting_pool')", "Water"),
	OsmSelectorPolygon("water = 'pond'", "Pond"),
	OsmSelectorPolygon("water in ('reservoir', 'basin') or landuse = 'reservoir'", "Reservoir"),
	OsmSelectorPolygon("water = 'lagoon'", "Lagoon"),
	OsmSelectorPolygon("waterway = 'dock' or water = 'harbour'", "Port"),
	OsmSelectorPolygon("waterway = 'weir'", "BuiltUpCover"),
	OsmSelectorPolygon("waterway = 'dam'", "GrassCover"),
	OsmSelectorPolygon("water = 'canal'", "Canal"),
	OsmSelectorPolygon("water in ('ditch', 'drain', 'stream_pool') and (intermittent = 'no' and seasonal is NULL)", "Stream"),
	OsmSelectorPolygon("water in ('ditch', 'drain', 'stream_pool') and (intermittent = 'yes' or seasonal is not NULL)", "IntermittentStream"),
	OsmSelectorPolygon("building != 'yes'", "BuiltUpCover"),
	OsmSelectorPolygon("highway in ('turning_circle', 'services') or parking = 'site'", "Asphalt"),
	OsmSelectorLine("highway in ('motorway', 'motorway_link', 'motorway_junction')", "Road", 12),
	OsmSelectorLine("highway in ('trunk', 'trunk_link')", "Road", 10),
	OsmSelectorLine("highway in ('primary', 'primary_link')", "Road", 8),
	OsmSelectorLine("highway in ('secondary', 'secondary_link')", "Road", 7),
	OsmSelectorLine("highway in ('tertiary', 'tertiary_link')", "Road", 6),
	OsmSelectorLine("highway in ('residential', 'living_street', 'unknown', 'unclassified', 'road')", "Road", 4),
	OsmSelectorLine("highway in ('service', 'track_grade1', 'busway')", "Road", 3),
	#OsmSelectorLine("highway in ('track', 'track_grade2')", "Gravel", 3),
	OsmSelectorLine("highway in ('track_grade3', 'track_grade4')", "Sand", 2),
	OsmSelectorLine("highway = 'track_grade4'", "GrassCover", 1),
	#OsmSelectorLine("highway = 'track_grade5'", "Dirt", 2),
	#OsmSelectorLine("highway in ('bridleway', 'path')", "Dirt", 1),
	OsmSelectorLine("highway in ('footway', 'cycleway')", "Asphalt", 1),
	OsmSelectorLine("railway in ('rail', 'light_rail')", "Railroad", 1),
	OsmSelectorLine("railway in ('narrow_gauge', 'tram')", "Railroad", 0.5),
	OsmSelectorLine("waterway = 'river'", "River", 5),
	OsmSelectorLine("waterway = 'stream' and (intermittent = 'no' and seasonal is NULL)", "Stream", 2),
	OsmSelectorLine("waterway = 'stream' and (intermittent = 'yes' or seasonal is not NULL)", "IntermittentStream", 2),
	OsmSelectorLine("waterway = 'canal'", "Canal", 10),
	OsmSelectorLine("waterway = 'ditch' and (intermittent = 'no' and seasonal is NULL)", "Stream", 1),
	OsmSelectorLine("waterway = 'ditch' and (intermittent = 'yes' or seasonal is not NULL)", "IntermittentStream", 1),
	OsmSelectorLine("waterway = 'drain' and (intermittent = 'no' and seasonal is NULL)", "Stream", 0.5),
	OsmSelectorLine("waterway = 'drain' and (intermittent = 'yes' or seasonal is not NULL)", "IntermittentStream", 0.5),
]

_region_boundary_cache = {}

def get_region_boundary(region: str) -> shapely.geometry.Polygon:
	if region in _region_boundary_cache:
		return _region_boundary_cache[region]
	
	url = GEOFABRIK_DOWNLOAD_URL + region + ".poly"
	cached_path = get_cached_file(url)
	with open(cached_path, "r") as f:
		coordpairs = list(map(str.split, filter(None, map(str.strip, f.readlines()))))
	coords = []
	for coordpair in coordpairs:
		if len(coordpair) != 2:
			continue
		coords.append((float(coordpair[0]), float(coordpair[1])))
	_region_boundary_cache[region] = shapely.geometry.Polygon(coords)
	return _region_boundary_cache[region]

def find_region(coord: Coord) -> str:
	region = None
	continent = None
	for continent in GEOFABRIK_REGIONS:
		boundary = get_region_boundary(continent)
		if boundary.contains(shapely.geometry.Point(coord.lon, coord.lat)):
			break
	
	if not continent:
		get_logger().warn(f"Warning: found no continent for lon={coord.lon} lat={coord.lat} !")
		return
	
	for region in GEOFABRIK_REGIONS[continent]:
		boundary = get_region_boundary(continent + "/" + region)
		if boundary.contains(shapely.geometry.Point(coord.lon, coord.lat)):
			break
	
	if region:
		return continent + "/" + region
	else:
		return continent

def get_airport_tiles(airports: typing.Iterable[aptdat.Airport]) -> list[Rectangle]:
	tiles = []
	for airport in airports:
		ll = [airport.bbox.left, airport.bbox.bottom]
		ll[1] = ll[1] - (ll[1] % FG_TILE_HEIGHT)
		ll[0] = ll[0] - (ll[0] % get_fg_tile_span(ll[1]))
		
		ur = [airport.bbox.right, airport.bbox.top]
		ur[1] = ur[1] + (FG_TILE_HEIGHT - (ur[1] % FG_TILE_HEIGHT))
		ur[0] = ur[0] + (get_fg_tile_span(ur[1]) - (ur[0] % get_fg_tile_span(ur[1])))
		
		if ll[1] < -90:
			ll[1] = -(ll[1] + 180)
			ll[0] += 180
		if ll[0] > 180:
			ll[0] -= 360
		
		tile = Rectangle(ll, ur)
		tiles.append(tile)
	return tiles

def find_osm_regions(bboxes: typing.Iterable[Rectangle]):
	regions = set()
	for bbox in bboxes:
		regions.add(find_region(bbox.ll))
		regions.add(find_region(bbox.ul))
		regions.add(find_region(bbox.ur))
		regions.add(find_region(bbox.lr))
	regions.discard(None)
	return regions

def download_osm_data(regions: typing.Iterable[str], workspace: str):
	osm_data_folder = os.path.join(workspace, "data", "osm")
	os.makedirs(osm_data_folder, exist_ok=True)
	
	osm_zips = []
	any_data_files_updated = False
	pbar = tqdm.tqdm(desc="Downloading OSM landuse data for regions", total=len(regions), unit=" regions")
	for i, region in enumerate(regions):
		path = os.path.join(osm_data_folder, region.split("/")[-1] + ".osm.pbf")
		osm_zips.append(path)
		old_mtime = os.path.getmtime(path) if os.path.exists(path) else -1
		pbar.update(1)
		if not download(
			GEOFABRIK_DOWNLOAD_URL + region + "-latest.osm.pbf",
			path,
			prolog=f"Downloading OSM landuse data … {i + 1} of {len(regions)} ({region}) - ",
		):
			sys.exit(1)
		
		if old_mtime != os.path.getmtime(path):
			any_data_files_updated = True
	
	if not download(
		"https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip",
		os.path.join(osm_data_folder, "land-polygons.zip"),
		prolog=f"Downloading OSM landmass polygons - "
	):
		sys.exit(1)
	
	padded_print(f"Extracting OSM landmass polygons …")
	zip_path = os.path.join(osm_data_folder, "land-polygons.zip")
	zf = zipfile.ZipFile(zip_path, mode="r")
	for zip_info in zf.infolist():
		if zip_info.is_dir():
			continue
		zip_info.filename = os.path.basename(zip_info.filename)
		if zip_info.filename == "README.txt":
			continue
		out_path = os.path.join(osm_data_folder, zip_info.filename)
		if not os.path.exists(out_path) or os.path.getmtime(zip_path) >= os.path.getmtime(out_path):
			zf.extract(zip_info, osm_data_folder)
			any_data_files_updated = True

def download_dem_data(bboxes: typing.Iterable[Rectangle], workspace: str):
	dem_data_folder = os.path.join(workspace, "data", "dem")
	os.makedirs(dem_data_folder, exist_ok=True)
	dempkgs = {}
	demzips = set()
	
	
	for i, bbox in enumerate(bboxes):
		padded_print(f"Searching elevation data packages … {i + 1} of {len(bboxes)}", end="\r")
		demsearch = requests.get(
			DEMSEARCH_URL.format(lon_ll=bbox.left, lat_ll=bbox.bottom, lon_ur=bbox.right, lat_ur=bbox.top)
		)
		if demsearch.status_code >= 400:
			print(f"\nError {r.status_code}: {url}")
			sys.exit(1)
		
		for dempkg in demsearch.json():
			dempkgs[dempkg["name"]] = dempkg
	padded_print(f"Searching elevation data packages … {len(bboxes)} of {len(bboxes)}")
	
	
	for i, dempkg in enumerate(dempkgs.values()):
		path = os.path.join(dem_data_folder, dempkg["name"])
		if not download(
			dempkg["link"], path, 
			prolog=f"Downloading elevation data packages … {i + 1} of {len(dempkgs)} ({dempkg['name']}) - ",
		):
			sys.exit(1)
		
		demzips.add(path)
	
	any_data_files_updated = False
	for i, demzip in enumerate(demzips):
		padded_print(f"Extracting elevation data … {i + 1} of {len(demzips)} ({os.path.split(demzip)[-1]})", end="\r")
		zf = zipfile.ZipFile(demzip, mode="r")
		for zip_info in zf.infolist():
			if zip_info.is_dir():
				continue
			zip_info.filename = os.path.basename(zip_info.filename)
			dem_tile_path = os.path.join(dem_data_folder, zip_info.filename)
			if not os.path.exists(dem_tile_path) or os.path.getmtime(demzip) >= os.path.getmtime(dem_tile_path):
				zf.extract(zip_info, dem_data_folder)
				any_data_files_updated = True
	padded_print(f"Extracting elevation data … {len(demzips)} of {len(demzips)}")
	
	return any_data_files_updated

def process_dem_data(workspace: str, bboxes: typing.Iterable[Rectangle]):
	dem_data_folder = os.path.join(workspace, "data", "dem")
	dem_work_folder = os.path.join(workspace, 'work', 'dem')
	os.makedirs(dem_work_folder, exist_ok=True)
	hgtfiles = sorted(find_input_files(dem_data_folder, suffix=".hgt"), reverse=True)
	any_files_updated = False
	timestamp_file = os.path.join(dem_data_folder, "gdalchop")
	ts = read_timestamp(timestamp_file)
	for i, bbox in enumerate(bboxes):
		padded_print(f"Chopping elevation data … {i + 1} of {len(bboxes)} ((n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right})", end="\r")
		tile_paths = list(map(lambda s: s + ".arr.gz", get_fg_tile_paths(bbox)))
		if get_newest_mtime(hgtfiles) < ts and all(os.path.exists(p) for p in tile_paths) and get_newest_mtime(tile_paths) <= ts:
			continue
		
		any_files_updated = True
		hgtfiles_string = " ".join(map(quote, hgtfiles))
		cmd = f"gdalchop {quote(dem_work_folder)} {hgtfiles_string} -- {' '.join(map(str, get_fg_tile_indices(bbox)))}"
		get_logger().debug(f"Running command: {cmd}")
		p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
		if p.returncode != 0:
			log_path = os.path.join(workspace, "log", "dem", f"N{bbox.top}E{bbox.left}S{bbox.bottom}W{bbox.right}.log")
			os.makedirs(os.path.join(workspace, "log", "dem"), exist_ok=True)
			with open(log_path, "wb") as log_file:
				log_file.write(p.stdout)
			get_logger().fatal(f"\nCommand '{cmd}' exited with return code {p.returncode} - see {log_path} for details.")
			sys.exit(1)
	padded_print(f"Chopping elevation data … {i + 1} of {len(bboxes)} ((n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right})")
	write_timestamp(timestamp_file)
	
	num_arrfiles = len(find_input_files(dem_work_folder, suffix=".arr.gz"))
	cmd = f"terrafit -m 1000 -x 20000 -e 5 {quote(dem_work_folder)}"
	get_logger().debug(f"Running command: {cmd}")
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True, bufsize=1)
	i = 1
	cur_path = ""
	for line in p.stdout:
		line = line.strip().split()
		if len(line) >= 3 and line[2] in ("Skipping", "Working"):
			i += 1
			if line[2] == "Working":
				cur_path = line[6][:-2]
				any_files_updated = True
		else:
			p.poll()
		padded_print(f"Fitting elevation data … {i + 1} of {num_arrfiles} ({os.path.split(cur_path)[-1]})", end="\r")
		if p.returncode != None and p.returncode != 0:
			log_path = os.path.join(workspace, "log", "dem", os.path.split(arrfile)[-1])
			os.makedirs(os.path.join(workspace, "log", "dem"))
			with open(log_path, "wb") as log_file:
				log_file.write(p.stdout)
			get_logger().fatal(f"\nCommand '{cmd}' exited with return code {p.returncode} - see {log_path} for details.")
			sys.exit(1)
	padded_print(f"Fitting elevation data … {num_arrfiles} of {num_arrfiles}")
	
	return any_files_updated

def process_airports(workspace, aptdat_files):
	apt_data_folder = os.path.join(workspace, "data", "apt")
	work_folder = os.path.join(workspace, "work")
	dem_work_folder = os.path.join(workspace, "work", "dem")
	airportobj_folder = os.path.join(work_folder, "AirportObj")
	airportarea_folder = os.path.join(work_folder, "AirportArea")
	os.makedirs(apt_data_folder, exist_ok=True)
	
	any_files_updated = False
	
	genapts_possibilities = ["genapts", "genapts850"]
	genapts = None
	for genapts_possibility in genapts_possibilities:
		if shutil.which(genapts_possibility):
			genapts = genapts_possibility
			break
	
	if not genapts:
		get_logger().fatal("No genapts executable found, cannot build airports - exiting !")
		sys.exit(1)
	
	timestamp_file = os.path.join(apt_data_folder, "genapts")
	ts = read_timestamp(timestamp_file)
	for i, aptdat_file in enumerate(aptdat_files):
		padded_print(f"Processing apt.dat files … {i + 1} of {len(aptdat_files)} ({os.path.basename(aptdat_file)})", end="\r")
		if ts > os.path.getmtime(aptdat_file) and os.path.exists(airportarea_folder) and os.path.exists(airportobj_folder) \
			and get_newest_mtime((airportarea_folder, airportobj_folder)) < ts:
			continue
		
		any_files_updated = True
		
		cmd = f"{quote(genapts)} --input={quote(aptdat_file)} --work={quote(work_folder)} --dem-path=dem --max-slope=1"
		get_logger().debug(f"Running command: {cmd}")
		p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
		if p.returncode != 0:
			log_path = os.path.join(workspace, "log", "apt", os.path.split(aptdat_file)[-1])
			os.makedirs(os.path.join(workspace, "log", "apt"), exist_ok=True)
			with open(log_path, "wb") as log_file:
				log_file.write(p.stdout)
			get_logger().fatal(f"\nCommand '{cmd}' exited with return code {p.returncode} - see {log_path} for details.")
			sys.exit(1)
	padded_print(f"Processing apt.dat files … {len(aptdat_files)} of {len(aptdat_files)} ({os.path.basename(aptdat_file)})")
	write_timestamp(aptdat_file)
	
	return any_files_updated

def ogr_decode(workspace, bbox, cmd, material, work_dir, data_file):
	timestamp_file = os.path.join(os.path.dirname(data_file), "ogr-decode_" + os.path.basename(data_file) + "_" + material)
	ts = read_timestamp(timestamp_file)
	if os.path.exists(work_dir) and ts > os.path.getmtime(data_file):
		return False
	
	env = os.environ.copy()
	if not "OSM_CONFIG_FILE" in env:
		env["OSM_CONFIG_FILE"] = importlib_resources_files("fgtools.scenery").joinpath("osmconf.ini")
	get_logger().debug(f"Running command: {cmd}")
	p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, env=env)
	if p.returncode != 0:
		log_path = os.path.join(workspace, "log", "osm", os.path.split(timestamp_file)[-1])
		os.makedirs(os.path.join(workspace, "log", "osm"), exist_ok=True)
		with open(log_path, "wb") as log_file:
			log_file.write(p.stdout)
		get_logger().fatal(f"\nCommand '{cmd}' exited with return code {p.returncode} - see {log_path} for details.")
		sys.exit(1)
	
	write_timestamp(timestamp_file)
	return True

def ogr_decode_polygon(workspace, bbox, mapping):
	osm_data_folder = os.path.join(workspace, "data", "osm")
	data_file = os.path.join(osm_data_folder, f"N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf")
	work_dir = os.path.join(workspace, "work", mapping.material)
	cmd = f"ogr-decode --area-type {quote(mapping.material)} --where {quote(mapping.selector)} {quote(work_dir)} {quote(data_file)} multipolygons"
	return ogr_decode(workspace, bbox, cmd, mapping.material, work_dir, data_file)

def ogr_decode_line(workspace, bbox, mapping):
	osm_data_folder = os.path.join(workspace, "data", "osm")
	data_file = os.path.join(osm_data_folder, f"N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf")
	work_dir = os.path.join(workspace, "work", mapping.material)
	cmd = f"ogr-decode --line-width {quote(mapping.line_width)} --line-width-column width --area-type {quote(mapping.material)} --where {quote(mapping.selector)} {quote(work_dir)} {quote(data_file)} lines"
	return ogr_decode(workspace, bbox, cmd, mapping.material, work_dir, data_file)

def ogr_decode_point(workspace, bbox, mapping):
	osm_data_folder = os.path.join(workspace, "data", "osm")
	data_file = os.path.join(osm_data_folder, f"N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf")
	work_dir = os.path.join(workspace, "work", mapping.material)
	cmd = f"ogr-decode --point-width {quote(mapping.line_width)} --area-type {quote(mapping.material)} --where {quote(mapping.selector)} {quote(work_dir)} {quote(data_file)} points"
	return ogr_decode(workspace, bbox, cmd, mapping.material, work_dir, data_file)

def process_landuse_data(workspace: str, bboxes: typing.Iterable[Rectangle], regions: typing.Iterable[str]):
	osm_data_folder = os.path.join(workspace, "data", "osm")
	landmass_file = os.path.join(osm_data_folder, "land_polygons.shp")
	
	any_files_updated = False
	for i, bbox in enumerate(bboxes):
		any_data_files_updated = False
		for region in regions:
			padded_print(f"Extracting needed OSM data … {i + 1} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right}) from {region}", end="\r")
			
			data_file = os.path.join(osm_data_folder, os.path.basename(region)) + ".osm.pbf"
			if not os.path.exists(data_file) or read_timestamp(data_file) > os.path.getmtime(data_file):
				continue
			
			any_data_files_updated = True
			run_command(
				"osmium extract " +
					" -b " + ",".join(map(str, (bbox.left, bbox.bottom, bbox.right, bbox.top))) + 
					" -O -o " + quote(os.path.join(osm_data_folder, f"{os.path.basename(region)}-N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf")) +
					f" {quote(data_file)}",
				os.path.join(workspace, "log", "osm", f"osmconvert_{os.path.basename(region)}_N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf")
			)
			
			write_timestamp(data_file)
		
		if any_data_files_updated:
			padded_print(f"Merging extracted OSM data … {i + 1} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right})", end="\r")
			data_files = [
				quote(os.path.join(
					osm_data_folder,
					f"{os.path.basename(region)}-N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf"
				))
				for region in regions
			]
			run_command(
				"osmium merge " + " ".join(data_files) + " --overwrite -o " +
					quote(os.path.join(osm_data_folder, f"N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf")),
				os.path.join(workspace, "log", "osm", f"osmconvert_N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.osm.pbf")
			)
		
		landmass_region_file = os.path.join(osm_data_folder, f"landmass-N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.shp")
		if not os.path.exists(landmass_region_file) or \
			read_timestamp(landmass_region_file) < max(os.path.getmtime(landmass_file), os.path.getmtime(landmass_region_file)):
			padded_print(f"Extracting needed OSM data … {i + 1} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right}) from landmass polygons", end="\r")
			run_command(
				f"ogr2ogr -clipsrc {bbox.left} {bbox.bottom} {bbox.right} {bbox.top} {quote(landmass_region_file)} {quote(landmass_file)}",
				os.path.join(workspace, "log", "osm", f"ogr2ogr_landmass_N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.shp")
			)
			write_timestamp(landmass_region_file)
			any_files_updated = True
	
	padded_print(f"Extracting needed OSM data … {len(bboxes)} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right})")
	
	for i, bbox in enumerate(bboxes):
		for j, mapping in enumerate(OSM_MATERIAL_MAPPINGS):
			padded_print(f"Decoding OSM data … {i + 1} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right}), landuse class {j} of {len(OSM_MATERIAL_MAPPINGS)} ({mapping.material})", end="\r")
			if isinstance(mapping, OsmSelectorPolygon):
				any_files_updated |= ogr_decode_polygon(workspace, bbox, mapping)
			elif isinstance(mapping, OsmSelectorLine):
				any_files_updated |= ogr_decode_line(workspace, bbox, mapping)
			elif isinstance(mapping, OsmSelectorPoint):
				any_files_updated |= ogr_decode_point(workspace, bbox, mapping)
		padded_print(f"Decoding OSM data … {i + 1} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right}), landmass", end="\r")
		
		data_file = os.path.join(osm_data_folder, f"landmass-N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}.shp")
		work_dir = os.path.join(workspace, "work", "Default")
		cmd = f"ogr-decode --area-type Default {quote(work_dir)} {quote(data_file)}"
		any_files_updated |= ogr_decode(workspace, bbox, cmd, "Default", work_dir, data_file)
		
	padded_print(f"Decoding OSM data … {len(bboxes)} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right})")
	return any_files_updated

def generate_terrain(workspace: str, bboxes: typing.Iterable[Rectangle], output_path: str, num_threads: int=0):
	work_dir = os.path.join(workspace, "work")
	output_path = os.path.join(output_path, "Terrain")
	num_threads = num_threads or (os.cpu_count() - 1) or 1
	for i, bbox in enumerate(bboxes):
			#f"--min-lon={bbox.left} --min-lat={bbox.bottom} --max-lon={bbox.right} --max-lat={bbox.top} " + \
		cmd = f"tg-construct --threads={num_threads} --output-dir={quote(output_path)} --work-dir={quote(work_dir)} " + \
			"--tile-id=" + " --tile-id=".join(map(str, get_fg_tile_indices(bbox))) + " " + \
			" ".join(sorted({quote(mapping.material) for mapping in OSM_MATERIAL_MAPPINGS}) + ["dem", "AirportArea", "AirportObj", "Default"])
		get_logger().debug(f"Running command: {cmd}")
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True, bufsize=1)
		j = 0
		num_tiles = 0
		for line in p.stdout:
			get_logger().debug("tg-construct printed: " + str(line.strip()))
			line = line.strip().split()
			status_text = ""
			if len(line) >= 3 and line[2].isnumeric():
				if line[4] == "Construct":
					j = int(line[8])
					num_tiles = int(line[10])
				else:
					status_text = " ".join(line[4:])
			p.poll()
			
			if len(line) >=  3:
				padded_print(f"Generating terrain … {i + 1} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right}) - working on tile {j} of {num_tiles} - {status_text or 'Construct'} for {line[2]}", end="\r")
			
			if p.returncode != None and p.returncode != 0:
				log_path = os.path.join(workspace, "log", "terrain", f"N{bbox.top}W{bbox.left}S{bbox.bottom}E{bbox.right}")
				os.makedirs(os.path.join(workspace, "log", "terrain"), exist_ok=True)
				with open(log_path, "w") as log_file:
					log_file.write(p.stdout.read())
				get_logger().fatal(f"\nCommand '{cmd}' exited with return code {p.returncode} - see {log_path} for details.")
				sys.exit(1)
	
	padded_print(f"Generating terrain … {len(bboxes)} of {len(bboxes)} (n={bbox.top} e={bbox.left} s={bbox.bottom} w={bbox.right})")

def main():
	argp = argparse.ArgumentParser(description="Automate the process of generating FightGear WS2.0 terrain, including fetching the landcover and elevation data")
	argp.add_argument(
		"-o", "--output",
		help="Scenery output folder (where the Terrain directory should be put in)",
		required=True
	)
	argp.add_argument(
		"-w", "--workspace",
		help="Workspace directory (where all data files, intermediary files, processed data etc. needed for the scenery build are stored)",
		required=True
	)
	argp.add_argument(
		"-i", "--input",
		help="One or more apt.dat files or directory(s) containing apt.dat files",
		required="True",
		nargs="+"
	)
	argp.add_argument(
		"--skip-data-downloads",
		help="Assume all data to be downloaded and up-to-date",
		action="store_true"
	)
	argp.add_argument(
		"-t", "--threads",
		help="Number of threads to use (default: (number of CPU cores) - 1)",
		default=0,
		type=int
	)
	argp.add_argument(
		"--loglevel",
		help="Set logging level",
		default="warning",
		choices=["debug", "info", "warn", "error", "fatal"]
	)
	
	args = argp.parse_args()
	
	osm_config_file = os.environ.get("OSM_CONFIG_FILE")
	if osm_config_file and not os.path.isfile(osm_config_file):
		get_logger().fatal(f"OSM config file {quote(osm_config_file)} does not exist / is not a file - exiting !")
	
	args.loglevel = args.loglevel.upper()
	if hasattr(logging, args.loglevel):
		loglevel = getattr(logging, args.loglevel)
	else:
		loglevel = logging.WARNING
	get_logger().setLevel(loglevel)
	
	aptdat_files = find_input_files(args.input, suffix=".dat")
	apt_reader = aptdat.ReaderWriterAptDat()
	apt_reader.read_multiple(aptdat_files)
	airports = apt_reader.get_airports()
	apt_tiles = get_airport_tiles(airports)
	
	osm_regions = find_osm_regions(apt_tiles)
	
	osm_data_updated = False
	dem_data_updated = False
	if not args.skip_data_downloads:
		osm_data_updated = download_osm_data(osm_regions, args.workspace)
		dem_data_updated = download_dem_data(apt_tiles, args.workspace)
	
	dem_data_processed = process_dem_data(args.workspace, apt_tiles)
	airports_processed = process_airports(args.workspace, aptdat_files)
	landuse_data_processed = process_landuse_data(args.workspace, apt_tiles, osm_regions)
	
	#if dem_data_processed or airports_processed or landuse_data_processed:
	generate_terrain(args.workspace, apt_tiles, args.output, args.threads)

if __name__ == "__main__":
	main()


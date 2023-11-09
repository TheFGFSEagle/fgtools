#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import sys
import argparse
import typing

from fgtools import btg, math
from fgtools.utils import padded_print, constants
from fgtools.utils.interpolator import Interpolator
from fgtools.geo import get_fg_tile_coords, get_fg_tile_span, get_fg_tile_index, get_fg_tile_path, get_fg_tile_bbox, Coord, FG_TILE_HEIGHT

VERTEX_DISTANCE_MAX_DEG = 0.000001

def create_border_data(tile_index: int, btg_file: str):
	print("\nCreating border data")
	tile_rect = get_fg_tile_bbox(tile_index)
	border_data = {edge: list() for edge in "nesw"}
	btg_object = btg.ReaderWriterBTG(btg_file)
	for v in btg_object.vertex_list.elements[0].items:
		if math.dist(v.coord.lon, tile_rect.left) < VERTEX_DISTANCE_MAX_DEG:
			border_data["e"].append(v.coord)
		if math.dist(v.coord.lon, tile_rect.right) < VERTEX_DISTANCE_MAX_DEG:
			border_data["w"].append(v.coord)
		if math.dist(v.coord.lat, tile_rect.bottom) < VERTEX_DISTANCE_MAX_DEG:
			border_data["s"].append(v.coord)
		if math.dist(v.coord.lat, tile_rect.top) < VERTEX_DISTANCE_MAX_DEG:
			border_data["n"].append(v.coord)
	
	border_data["n"].sort(key=lambda v: v.lon)
	border_data["s"].sort(key=lambda v: v.lon)
	border_data["e"].sort(key=lambda v: v.lat)
	border_data["w"].sort(key=lambda v: v.lat)
	
	return border_data

def read_border_data(border_file: str):
	border_data = {edge: list() for edge in "nesw"}
	with open(border_file, "r") as f:
		cur_side = ""
		for line in f:
			parts = line.strip().split(" ")
			if len(parts) == 0:
				continue
			if parts[0] in "nesw":
				cur_side = parts[0]
			else:
				border_data[cur_side].append(Coord(float(parts[0]), float(parts[1]), float(parts[2])))
	
	return border_data

def write_border_data(border_file: str, border_data: typing.Mapping[str, typing.Iterable[Coord]]):
	os.makedirs(os.path.dirname(border_file), exist_ok=True)
	with open(border_file, "w") as f:
		for side in "nesw":
			f.write(side + "\n")
			for c in border_data[side]:
				f.write(" ".join(map(str, [c.lon, c.lat, c.alt])) + "\n")

def get_border_data(tile_index: int, terrain_dir: str, border_dir: str):
	tile_path = get_fg_tile_path(tile_index)
	btg_file = os.path.join(terrain_dir, tile_path + ".btg.gz")
	if border_dir == "terrain-dir":
		border_dir == terrain_dir
	border_file = ""
	if border_dir != "direct":
		border_file = os.path.join(border_dir, tile_path) + "_edges.dat"
		if os.path.exists(border_file) and os.path.getmtime(border_file) > os.path.getmtime(btg_file):
			return read_border_data(border_file)
	
	border_data = create_border_data(tile_index, btg_file)
	if border_dir != "direct":
		write_border_data(border_file, border_data)
	return border_data

def process_btg_file(nth_input: int, total: int, tile_path: str, terrain_dir: str, border_dir: str):
	padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Calculating neighbor tile indices", end="\r")
	tile_index = int(os.path.split(tile_path)[-1].split(".")[0])
	tile_coord = Coord(get_fg_tile_coords(tile_index))
	tile_rect = get_fg_tile_bbox(tile_index)
	sibling_coords = {
		"n": tile_coord + (0, FG_TILE_HEIGHT),
		"e": tile_coord - (get_fg_tile_span(tile_coord.lat), 0),
		"s": tile_coord - (0, FG_TILE_HEIGHT),
		"w": tile_coord + (get_fg_tile_span(tile_coord.lat), 0),
	}
	
	sibling_indices = {}
	for side in sibling_coords:
		sibling_indices[side] = get_fg_tile_index(sibling_coords[side].lon, sibling_coords[side].lat)
	del sibling_coords

	sibling_borders = {}
	for i, side in enumerate(sibling_indices):
		padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Getting border data for neighbor BTG files ({i} of {len(sibling_indices)})", end="\r")
		border_data = get_border_data(sibling_indices[side], terrain_dir, border_dir)
		if side == "n":
			border_data = border_data["s"]
		elif side == "e":
			border_data = border_data["w"]
		elif side == "s":
			border_data = border_data["n"]
		elif side == "w":
			border_data = border_data["e"]
		sibling_borders[side] = border_data
	padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Getting border data for neighbor BTG files ({len(sibling_indices)} of {len(sibling_indices)})", end="\r")
	del sibling_indices
	
	sibling_border_interpolators = {}
	for i, side in enumerate(sibling_borders):
		padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Creating interpolation tables for border data ({i} of {len(sibling_borders)})", end="\r")
		sibling_border_interpolator = Interpolator()
		if side in "ns":
			attrib = "lon"
		else:
			attrib = "lat"
		
		for coord in sibling_borders[side]:
			sibling_border_interpolator.add_value(getattr(coord, attrib), coord.alt)
		sibling_border_interpolators[side] = sibling_border_interpolator
	padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Creating interpolation tables for border data ({len(sibling_borders)} of {len(sibling_borders)})", end="\r")
	
	padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Reading BTG file", end="\r")
	btg_object = btg.ReaderWriterBTG()
	btg_object.read(tile_path)
	
	tri_indices_to_process = []
	total_tris = sum(map(lambda obj: len(obj.elements), btg_object.triangle_faces))
	processed_tris = 0
	for i, obj in enumerate(btg_object.triangle_faces):
		for j, tri in enumerate(obj.elements):
			padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Finding triangles that need fixing ({processed_tris} of {total_tris})", end="\r")
			for vi in tri.vertex_indices:
				v = btg_object.vertex_list.elements[0].items[vi]
				if min(
					math.dist(v.coord.lon, tile_rect.left), math.dist(v.coord.lon, tile_rect.right),
					math.dist(v.coord.lat, tile_rect.bottom), math.dist(v.coord.lat, tile_rect.top),
				) < VERTEX_DISTANCE_MAX_DEG:
					tri_indices_to_process.append((i, j))
			processed_tris += 1
	padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Finding triangles that need fixing ({total_tris} of {total_tris})", end="\r")
	
	for i, (obj_index, tri_index) in enumerate(tri_indices_to_process):
		padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Fixing triangles ({i} of {len(tri_indices_to_process)})", end="\r")
		tri = btg_object.triangle_faces[obj_index].elements[tri_index]
		for vi in tri.vertex_indices:
			v = btg_object.vertex_list.elements[0].items[vi]
			if math.dist(v.coord.lon, tile_rect.left) < VERTEX_DISTANCE_MAX_DEG:
				v.coord.alt = sibling_border_interpolators["e"].interpolate(v.coord.lat)
			elif math.dist(v.coord.lon, tile_rect.right) < VERTEX_DISTANCE_MAX_DEG:
				v.coord.alt = sibling_border_interpolators["w"].interpolate(v.coord.lat)
			elif math.dist(v.coord.lat, tile_rect.bottom) < VERTEX_DISTANCE_MAX_DEG:
				v.coord.alt = sibling_border_interpolators["s"].interpolate(v.coord.lon)
			elif math.dist(v.coord.lat, tile_rect.top) < VERTEX_DISTANCE_MAX_DEG:
				v.coord.alt = sibling_border_interpolators["n"].interpolate(v.coord.lon)
	padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Fixing triangles ({len(tri_indices_to_process)} of {len(tri_indices_to_process)})", end="\r")
	
	padded_print(f"Processing BTG file {nth_input + 1} of {total} ({tile_path}) - Writing processed BTG file")
	center = Coord.from_cartesian(btg_object.bs.elements[0].x, btg_object.bs.elements[0].y, btg_object.bs.elements[0].z)
	btg_object.write(tile_path)

def map_border_data_dir(value):
	if value in ("terrain-dir", "direct"):
		return value
	elif value == "cache-dir":
		return os.path.join(constants.CACHEDIR, "ungap-btg", "tile-borders")
	elif "/" in value:
		return value
	else:
		raise argparse.ArgumentTypeError(f"unrecognized value for --border-dir: '{value}'")

def main():
	argp = argparse.ArgumentParser(description="Removes elevation differences between a BTG tile and the surrounding tiles")
	formatter_class=argparse.RawTextHelpFormatter
	argp.add_argument(
		"-i", "--input",
		help="BTG file(s) to fix",
		required=True,
		nargs="+"
	)
	argp.add_argument(
		"-t", "--terrain-dir",
		help="Terrain folder containing BTG files surrounding the input file(s)",
		required=True
	)
	argp.add_argument(
		"-b", "--border-dir",
		help="Set where to search for tile border files from a previous run of this script, possible values are:\n"
			"	\"terrain-dir\": use path from --terrain-dir. This is the default.\n"
			"	\"cache-dir\": use cache directory (" + map_border_data_dir("cache-dir") + ")"
			"	<path>: use the supplied path"
			"	\"direct\": read border data directly from the terrain files, very slow !\n"
			"	This is the default whenever no border data files are found\n"
			"	To use a non-existing directory make sure the path contains a slash, else it might not be recognised as a path !",
		type=map_border_data_dir
	)
	args = argp.parse_args()
	
	if not os.path.isdir(args.terrain_dir):
		print("Terrain directory {args.terrain_dir} does not exist / is not a directory !")
		sys.exit(1)
	
	for i, path in enumerate(args.input):
		process_btg_file(i, len(args.input), path, args.terrain_dir, args.border_dir)
	print()

if __name__ == '__main__':
	main()


#!/usr/bin/env python
#-*- coding:utf-8 -*-

import argparse
import os
import natsort
from fgtools.utils.interpolator import Interpolator


def parse_data_files(input_files, blade_angles):
	blade_angles = list(map(float, blade_angles))
	data = {}
	for file, angle in zip(input_files, blade_angles):
		data[angle] = {
			"Cp": Interpolator(),
			"Ct": Interpolator()
		}
		with open(file) as f:
			content = f.readlines()
		
		content = list(map(lambda s: s.strip().split("\t"), content))[2:]
		for line in content:
			av, ct, cp = float(line[0]), float(line[2]), float(line[3])
			data[angle]["Cp"].add_value(av, cp)
			data[angle]["Ct"].add_value(av, ct)
	
	return data


def make_tables(data, maximum, indentation="\t", resolution=0.05):
	if len(data.keys()) > 1:
		Cp = Ct = indentation * 4 + (indentation * 2).join(map(str, data.keys())) + "\n"
	else:
		Cp = Ct = ""
	
	av = 0
	while av <= maximum:
		av = round(av, 6)
		Cp += indentation * 2 + indentation + str(av) + indentation
		Ct += indentation * 2 + indentation + str(av) + indentation
		cps = []
		cts = []
		for angle in data:
			cps.append("%.6f" % round(data[angle]["Cp"].interpolate(av, sort=False), 6))
			cts.append("%.6f" % round(data[angle]["Ct"].interpolate(av, sort=False), 6))
		
		Cp += indentation.join(cps) + "\n"
		Ct += indentation.join(cts) + "\n"
		av += resolution
	return {"Cp":Cp, "Ct": Ct}		
				


def main():
	argp = argparse.ArgumentParser(description="javaprop2jsbcpct.py - converts JavaProp propeller data into Cp and Ct tables for a JSBsim propeller\nReplace the C_THRUST and C_POWER tables in your JSBsim propeller file with the output of this script.")
	
	argp.add_argument(
		"-i", "--input-file",
		help="Files to read JavaProp data from (one per blade angle)",
		required=True,
		nargs="+",
		dest="input_files"
	)
	
	argp.add_argument(
		"-b", "--blade-angle",
		help="Blade angles of the JavaProp data files (one per file)",
		required=True,
		nargs="+",
		dest="blade_angles"
	)
	
	argp.add_argument(
		"-m", "--max",
		help="Maximum advance ratio to output data for",
		required=True,
		type=float
	)
	
	argp.add_argument(
		"--interactive",
		action="store_true",
		help="Read JavaProp data from standard input instead of a file, ignoring --input-file (disabled by default)",
	)
	
	argp.add_argument(
		"--indentation",
		help="Indentation to use (the argument of this option will be used as one level of indentation), defaults to tabs",
		default="\t"
	)
	
	argp.add_argument(
		"-r", "--resolution",
		help="Advance ratio resolution to generate (default: 0.05)",
		type=float,
		default=0.05
	)
	
	args = argp.parse_args()
	
	paths = []
	
	for path in args.input_files:
		if not os.path.exists(path):
			print(f"Error: input file / directory {path} not found, exiting")
			sys.exit(1)
		
		if os.path.isfile(path):
			paths.append(path)
		else:
			for file in natsort.realsorted(os.listdir(path)):
				paths.append(os.path.join(path, file))
	
	if len(args.blade_angles) < len(paths):
		print("Error: less blade angles than input files")
	elif len(args.blade_angles) > len(paths):
		args.blade_angles, rest = args.blade_angles[:len(paths) + 1]
		print(f"Warning: skipping {len(rest)} blade angles because no corresponding data file was specified")
	
	data = parse_data_files(paths, args.blade_angles)
	output = make_tables(data, args.max, args.indentation, args.resolution)
	
	print(args.indentation + "<table name=\"C_THRUST\" type=\"internal\">")
	print(args.indentation * 2 + "<tableData>")
	print(output["Ct"])
	print(args.indentation * 2 + "</tableData>")
	print(args.indentation + "</table>")
	print(args.indentation)
	print(args.indentation + "<table name=\"C_POWER\" type=\"internal\">")
	print(args.indentation * 2 + "<tableData>")
	print(output["Cp"])
	print(args.indentation * 2 + "</tableData>")
	print(args.indentation + "</table>")

if __name__ == "__main__":
	main()



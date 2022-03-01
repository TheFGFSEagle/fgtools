#!/usr/bin/env python
#-*- coding:utf-8 -*-

import argparse
import os

def parse_data_files(input_files, blade_angles):
	blade_angles = list(map(float, blade_angles))
	data = {}
	for file, angle in zip(input_files, blade_angles):
		with open(file) as f:
			content = f.readlines()
		
		content = list(map(lambda s: s.strip().split("\t"), content))[2:]
		data[angle] = {}
		for line in content:
			data[angle][float(line[0])] = {"Ct": float(line[2]), "Cp": float(line[3])}
	
	return data


if __name__ == "__main__":
	argp = argparse.ArgumentParser(description="javaprop2jsbcpct.py - converts JavaProp propeller data into Cp and Ct tables for a JSBsim propelller")
	
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
		"--interactive",
		action="store_true",
		help="Read JavaProp data from standard input instead of a file, ignoring --input-file (disabled by default)",
	)
	
	argp.add_argument(
		"--indentation",
		help="Indentation to use (the argument of this option will be used as one level of indentation), defaults to tabs",
		default="\t"
	)
	
	args = argp.parse_args()
	
	for path in args.input_files:
		if not os.path.isfile(path):
			print(f"Error: input file {path} not found, exiting")
			sys.exit(1)
	
	if len(args.blade_angles) < len(args.input_files):
		print("Error: less blade angles than input files")
	elif len(args.blade_angles) > len(args.input_files):
		args.blade_angles, rest = args.blade_angles[:len(args.input_files)]
		print(f"Warning: skipping {len(rest)} blade angles because no corresponding data file was specified")
	
	data = parse_data_files(args.input_files, args.blade_angles)


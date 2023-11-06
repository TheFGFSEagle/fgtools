#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import argparse
import os

class SkipReason:
	NotFound = 0
	DirEmpty = 1
	NoSTG = 2

def read_stg_file(path):
	result = []
	offset = 0
	skipnext = False
	with open(path, "r") as fp:
		content = fp.readlines()
		for number, line in enumerate(content):
			line = line.strip()
			if line.startswith("#"): # is a comment
				if line.startswith("# offset"):
					offset = line.split(" ")[-1]
					result.append(line)
				elif line.startswith("# skipnext"):
					skipnext = True
			elif line.strip() == "": # empty line
				continue
			else: # is an object
				etype, *data = list(map(lambda s: s.strip(), line.split(" ")))
				if etype in ["OBJECT_SHARED", "OBJECT_STATIC"]:
					if len(data) == 5:
						objectfile, longitude, latitude, elevation, heading, pitch, roll = *data, 0, 0
					elif len(data) == 7:
						objectfile, longitude, latitude, elevation, heading, pitch, roll = data
					else:
						print(f"Warning: file {path}, line {number} is malformed - not converting entry")
						result.append(line)
						continue
					
					result.append({
						"etype": etype,
						"objectfile": objectfile,
						"longitude": longitude,
						"latitude": latitude,
						"elevation": float(elevation),
						"offset": float(offset),
						"heading": heading,
						"pitch": pitch,
						"roll": roll,
						"skip": skipnext
					})
					offset = 0
					skipnext = False
				else:
					print(f"Warning: skipping line {number} in {path} because type {etype} is not supported")
	return result

def read_stg_files(paths):
	stg_dict = dict.fromkeys(paths, {"infiles": [], "contents": []})
	for path in paths:
		if not os.path.exists(path):
			print(f"Warning: Input file / directory {path} does not exist, skipping")
			stg_dict[path] = SkipReason.NotFound
		elif os.path.isdir(path):
			for file in os.listdir(path):
				if os.splitext(path)[1] == ".stg":
					realpath = os.path.join(path, file)
					content = read_stg_file(realpath)
					stg_dict[path]["infiles"].append(file)
					stg_dict[path]["contents"].append(content)
			else:
				print(f"Warning: No STG file found in input directory {path}, skipping")
				stg_dict[path] = SkipReason.DirEmpty
		else:
			if os.path.splitext(path)[1] == ".stg":
				content = read_stg_file(path)
				stg_dict[path]["infiles"].append(path)
				stg_dict[path]["contents"].append(content)
			else:
				print(f"Warning: Input file {path} is not an STG file, skipping")
				stg_dict[path] = SkipReason.NoSTG
	return stg_dict

def write_xml_files(output_stg, outfiles):
	for i, path in enumerate(output_stg):
		if type(path) != str: # SkipReason
			continue
		for infile, content in zip(output_stg[path]["infiles"], output_stg[path]["contents"]):
			if len(outfiles) == 1:
				if outfiles[0] == "__INPUT__":
					outfile = infile
				else:
					outfile = outfiles[0]
			else:
				if i < len(outfiles):
					outfile = outfiles[i]
				else:
					outfile = outfiles[-1]
			
			with open(outfile, "w") as outfp:
				outfp.write("<?xml version=\"1.0\"?>\n")
				outfp.write("<PropertyList>\n")
				outfp.write("	<models>\n")
				
				for object in content:
					outfp.write("		<model>\n")
					outfp.write(f"			<legend>{object['objectfile'].split('/')[-1]}</legend>\n")
					outfp.write(f"			<pitch-deg>{object['pitch']}</pitch-deg>\n")
					outfp.write(f"			<roll-deg>{object['pitch']}</roll-deg>\n")
					outfp.write(f"			<heading-deg>{object['heading']}</heading-deg>\n")
					outfp.write(f"			<latitude-deg>{object['latitude']}</latitude-deg>\n")
					outfp.write(f"			<longitude-deg>{object['longitude']}</longitude-deg>\n")
					outfp.write(f"			<elevation-ft>{float(object['elevation']) * 3.2808399}</elevation-ft>\n")
					outfp.write(f"			<elevation-m>{object['elevation']}</elevation-m>\n")
					outfp.write(f"			<stg-heading-deg>{float(object['heading']) + 180}</stg-heading-deg>\n")
					outfp.write(f"			<stg-path>{os.path.abspath(path)}</stg-path>\n")
					
					objectpath = object["objectfile"]
					if object["etype"] == "OBJECT_STATIC":
						objectpath = path + "/" + objectpath
					outfp.write(f"			<path>{objectpath}</path>\n")
					
					line = f"{object['etype']} {object['objectfile']} {object['longitude']} {object['latitude']} {object['elevation'] + object['offset']} {object['heading']} {object['pitch']} {object['roll']}"
					outfp.write(f"			<object-line>{line}</object-line>\n")
					outfp.write("		</model>\n")
					
				outfp.write("	</models>\n")
				outfp.write("</PropertyList>\n")

def main():
	argp = argparse.ArgumentParser(description="Perform various STG file operations such as recalculating the elevation of models")
	
	argp.add_argument(
		"-i", "--input",
		help="Input STG file. Mandatory, more than one file / directory can be passed",
		nargs="+",
		required=True
	)
	
	argp.add_argument(
		"-o", "--output",
		help="Output STG file. Default is to overwrite the input file(s).",
		nargs="+",
		default=["__INPUT__"]
	)
	
	args = argp.parse_args()
	infiles = args.input
	outfiles = args.output
	
	input_stg = read_stg_files(infiles)
	exitstatus = write_xml_files(input_stg, outfiles)

if __name__ == "__main__":
	main()

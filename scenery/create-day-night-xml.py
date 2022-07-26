#!/usr/bin/env python

import os, sys, argparse

def get_texture_paths(folder="."):
	texture_paths = {}
	for name in os.listdir(folder):
		path = os.path.relpath(os.path.join(folder, name), start=folder)
		if name.endswith(".ac"):
			with open(path, "r") as f:
				if not path in texture_paths:
					texture_paths[path] = {}
				object = ""
				for line in f:
					if line.strip().startswith("name"):
						object = line.split('"')[1]
						if object == "world":
							object = ""
							continue
					
					if line.strip().startswith("texture") and object:
						texture_path = line.split('"')[1]
						if not texture_path in texture_paths[path]:
							texture_paths[path][texture_path] = []
						texture_paths[path][texture_path].append(object)
				
				if not texture_paths[path]:
					print(path, "contains no texture, skipping")
	
	if not texture_paths:
		print(os.path.abspath(folder), "does not contain any AC files - exiting")
		sys.exit(1)
	
	return texture_paths

def write_xml_files(texture_paths, lit_suffix, overwrite):
	for ac_path in texture_paths:
		xml_path = ac_path.replace(".ac", ".xml")
		if os.path.isfile(xml_path) and not overwrite:
			print("XML file", xml_path, "already exists - skipping")
			continue
		
		with open(xml_path, "w") as xml_f:
			xml_f.write("""<?xml version="1.0" encoding="utf-8"?>
<PropertyList>
	<path>%s</path>""" % ac_path)
			
			for texture_path in texture_paths[ac_path]:
				texture_lit_path = texture_path.split(".")
				texture_lit_path[-2] += lit_suffix
				texture_lit_path = ".".join(texture_lit_path)
		
				if not os.path.isfile(texture_lit_path):
					print("Night texture", texture_lit_path, "does not exist - skipping objects")
					continue
				
				xml_f.write("""
	<animation>
		<condition>
			<greater-than>
				<property>/sim/time/sun-angle-rad</property>
				<value>1.49</value>
			</greater-than>
		 </condition>
		<type>material</type>""")
				
				for object in texture_paths[ac_path][texture_path]:
					xml_f.write("		<object-name>%s</object-name>" % object)
				
				xml_f.write("""		<emission>
			 <red>1</red>
			 <green>1</green>
			 <blue>1</blue>
		 </emission>
		 <texture>%s</texture>
	</animation>""" % texture_lit_path)
				xml_f.write("""
	
	<animation>
		<type>material</type>
		<condition>
			<less-than-equals>
				<property>/sim/time/sun-angle-rad</property>
				<value>1.49</value>
			</less-than-equals>
		</condition>""")
				
				for object in texture_paths[ac_path][texture_path]:
					xml_f.write("		<object-name>%s</object-name>" % object)
				
				xml_f.write("""		<emission>
			<red>0</red>
			<green>0</green>
			<blue>0</blue>
		</emission>
		<texture>%s</texture>""" % texture_path)
			
				xml_f.write("</animation>")
		
			xml_f.write("</PropertyList>\n")

def main():
	argp = argparse.ArgumentParser()
	
	argp.add_argument("-o", "--overwrite",
		help="Whether to overwrite XML files if any already exist, defaults to not overwriting",
		action="store_true"
	)
	
	argp.add_argument("-s", "--lit-suffix",
		help="What suffix the lit texture has (of the name itself, not the file extension), default is _LIT",
		default="_LIT"
	)
	
	argp.add_argument("folder",
		help="Folder / directory where the AC files and textures are in, default is working directory",
		default="."
	)
	
	args = argp.parse_args()
	
	if not os.path.isdir(args.folder):
		print("Folder", args.folder, "does not exist - exiting")
		sys.exit(1)
	
	texture_paths = get_texture_paths(args.folder)
	write_xml_files(texture_paths, args.lit_suffix, args.overwrite)

if __name__ == "__main__":
	main()


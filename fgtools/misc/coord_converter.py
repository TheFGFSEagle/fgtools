#!/usr/bin/env python
#-*- coding:utf-8 -*-

import argparse

def format_skyvector(lon, lat):
	lond, lonm = divmod(abs(lon), 1)
	lonm = lonm * 60
	latd, latm = divmod(abs(lat), 1)
	latm = latm * 60
	ew = "EW"[int(lon < 0)]
	ns = "NS"[int(lat < 0)]
	return f"{int(latd):02d}{int(latm * 100):04d}{ns}{int(lond):03d}{int(lonm * 100):04d}{ew}"

def main():
	argp = argparse.ArgumentParser(description="Convert GPS coordinates between different formats")
	
	argp.add_argument(
		"--lon",
		help="Input longitude",
		required=True,
		type=float
	)
	
	argp.add_argument(
		"--lat",
		help="Input latitude",
		required=True,
		type=float
	)
	
	argp.add_argument(
		"-f", "--format",
		help="Output format",
		required=True,
		choices=["dmd", "dms", "skyvector"]
	)
	
	args = argp.parse_args()
	
	if args.format == "skyvector":
		result = format_skyvector(args.lon, args.lat)
	else:
		result = "Output format is not implemented yet"
	print(result)

if __name__ == '__main__':
	main()




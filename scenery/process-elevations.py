#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Small wrapper script for gdalchop that, if you are following the standar TerraGear directory structure,
# can be run without arguments

import sys
import argparse
import subprocess

from tgtools import constants

argp = argparse.ArgumentParser(description="process-elevations.py - process a directory of elevation data files with gdalchop and terrafit")

argp.add_argument(
	"-i", "--input-folder",
	help="folder containing the raw elevation files (default: %(default)s)",
	default="./data/elevation",
	metavar="INPUT",
)

argp.add_argument(
	"-o", "--output-folder",
	help="where to put the produced files (default: %(default)s)",
	default="./work/elevation",
	metavar="OUTPUT"
)

argp.add_argument(
	"-v", "--version",
	action="version",
	version=f"FGTools {constants.__versionstr__}"
)

args = argp.parse_args()

chop = subprocess.Popen(["gdalchop", args.output_folder, args.input_folder], stdout=sys.stdout, stderr=sys.stderr)
exit = chop.run()
sys.exit(exit)


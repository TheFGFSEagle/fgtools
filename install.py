#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Installer script for the main scripts and modules of fgtools
import os
import sys
import argparse
import shutil
import site

from fgtools.utils import constants

argp = argparse.ArgumentParser(description="install.py - installs the TerraGear tools so that they can be run like any other executable")

argp.add_argument(
	"-p", "--prefix",
	help="Installation prefix (default: %(default)s)",
	default=os.environ.get("FGTOOLSPREFIX", os.path.join(constants.HOME, ".local")))
)

argp.add_argument(
	"--add-to-path",
	help="whether to modify your $HOME/.profile file to have the folder containing the scripts in your path (default: %(default)s",
	default="yes",
	choices=["yes", "no"]
)

args = argp.parse_args()

SCRIPTDIR = os.path.dirname(os.path.abspath(__name__))
BINDIR = os.path.join(args.prefix, "bin")
PYLIBDIR = os.path.join(args.prefix, "lib", "python3")

print(f"Installing to {args.prefix}")

print("Installing modules …")
shutil.copytree(os.path.join(SCRIPTDIR, constants.MODULE), PYLIBDIR)

print("Installing scripts …")
for script in constants.SCRIPTS:
	shutil.copy2(os.path.join(SCRIPTDIR, script), BINDIR)

if not BINDIR in os.environ.get("PATH", "").split(os.pathsep):
	if args.add_to_path:
		print(f"Adding {BINDIR} to your $PATH …")
		
		if os.name == "posix": # Linux, MacOS
			with open(os.path.join(constants.HOME, ".profile"), "a") as f:
				f.write(f"export PATH=\"$PATH{os.pathsep}{BINDIR}\"")
		else: # probably Windows
			os.system(f"setx PATH \"%PATH%{os.pathsep}{BINDIR}\"")
	else:
		print(f"WARNING: {BINDIR} was not added to your $PATH - please do that manually")

if not LIBDIR in os.environ.get("PYTHONPATH", "").split(os.pathsep):
	print(f"Adding {LIBDIR} to your $PYTHONPATH …")
	
	if not os.path.isdir(site.USER_SITE):
		os.mkdirs(site.USER_SITE)
	
	mode = "a"
	if not os.path.isfile(os.path.join(site.USER_SITE, "sitecustomize.py")):
		mode = "w"
	
	with open(os.path.join(site.USER_SITE, "sitecustomize.py"), mode) as f:
		f.write(f"import site; site.addsitedir({LIBDIR})")

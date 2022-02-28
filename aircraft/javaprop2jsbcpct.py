#!/usr/bin/env python
#-*- coding:utf-8 -*-

import argparse

if __name__ == "__main__":
	argp = argparse.ArgumentParser(description="javaprop2jsbcpct.py - converts JavaProp propeller data into Cp and Ct tables for a JSBsim propelller")
	
	argp.add_argument(
		"-i", "--input-file",
		help="File to read JavaProp data from",
		required=True
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
	print(args)

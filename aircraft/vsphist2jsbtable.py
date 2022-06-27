#!/usr/bin/env python
#-*- coding:utf-8 -*-

import argparse
import os, sys
from fgtools.utils.interpolator import Interpolator

class Case:
	def __init__(self, textcase):
		textcase.pop(0) # get rid of the Name Value Unit legend line
		self.Sref = float(textcase.pop(0).split()[1])
		self.Bref = float(textcase.pop(0).split()[1])
		self.Cref = float(textcase.pop(0).split()[1])
		self.Xcg = float(textcase.pop(0).split()[1])
		self.Ycg = float(textcase.pop(0).split()[1])
		self.Zcg = float(textcase.pop(0).split()[1])
		self.Mach = float(textcase.pop(0).split()[1])
		self.AoA = float(textcase.pop(0).split()[1])
		self.Beta = float(textcase.pop(0).split()[1])
		self.Rho = float(textcase.pop(0).split()[1])
		self.Vinf = float(textcase.pop(0).split()[1])
		self.RollRate = float(textcase.pop(0).split()[1])
		self.PitchRate = float(textcase.pop(0).split()[1])
		self.YawRate = float(textcase.pop(0).split()[1])
		textcase.pop(0) # get rid of the Solver case line
		textcase.pop(0) # get rid of another legend line
		lastiterindex = textcase.index("Skin Friction Drag Break Out:") - 1
		self.CL, self.CDo, self.CDi, self.CDtot, self.CS, self.LD, self.E, self.CFx, self.CFy, self.CFz, self.CMx, self.CMy, self.CMz, self.CDtrefftz, self.TQS = map(float, textcase.pop(lastiterindex).split()[4:]) # we don't need Mach, AoA, Beta again
	
	def __str__(self):
		return "Case(" + ", ".join(str(k) + " = " + str(v) for k, v in vars(self).items()) + ")"
	
	def __repr__(self):
		return self.__str__()

def get_cases(path):
	path = os.path.abspath(path)
	
	if not path.endswith(".history"):
		print("The specified file", path, "is not a VSPAERO .history file - exiting")
		sys.exit(1)
	
	with open(path, "r") as histf:
		textcases = []
		lines = histf.readlines()[1:]
		textcase = []
		cases = {}
		
		for line in lines:
			if line.startswith("****"):
				textcases.append(list(filter(None, textcase)))
				textcase = []
				continue
			textcase.append(line.strip())
		textcases.append(list(filter(None, textcase)))
		
		for textcase in textcases:
			case = Case(textcase)
			if not case.AoA in cases:
				cases[case.AoA] = {}
			cases[case.AoA][case.Beta] = case
	
	return cases

def print_table(cases, coeff, indent, precision):
	coeffs = {}
	for AoA in cases:
		for Beta in cases[AoA]:
			if not hasattr(cases[AoA][Beta], coeff):
				print("The coefficient", coeff, "does not exist in the specified .history file - exiting")
				sys.exit(1)
			
			if not AoA in coeffs:
				coeffs[AoA] = {}
			coeffs[AoA][Beta] = getattr(cases[AoA][Beta], coeff)
	
	print("<table>")
	print(indent + '<independentVar lookup="row">aero/alpha-deg</independentVar>')
	print(indent + '<independentVar lookup="column">aero/beta-deg</independentVar>')
	#print(indent + '<independentVar lookup="table">velocities/mach</independentVar>')
	print(indent + "<tableData>")
	print(indent + indent + indent + indent.join(map(str, coeffs[list(coeffs.keys())[0]].keys())))
	for AoA in coeffs:
		print(indent + indent + str(AoA), end="")
		for Beta in coeffs[AoA]:
			print(indent + ("%." + str(precision) + "f") % coeffs[AoA][Beta], end="")
		print()
	print(indent + "</tableData>")
	print("</table>")


if __name__ == "__main__":
	argp = argparse.ArgumentParser(description="vsphist2jsbtable.py - Takes a VSPAERO .history file and a coefficient as input and outputs a JSBSim interpolation table for that coefficient from the VSPAERO cases")
	
	argp.add_argument(
		"-c", "--coeff",
		help="Name of the coefficient to produce a table for",
		required=True,
	)
	
	argp.add_argument(
		"--indentation",
		help="The argument of this option will be used as one level of indentation, defaults to a tab",
		default="\t"
	)
	
	argp.add_argument(
		"-p", "--precision",
		help="How many decimal places the numbers in the table should have, defaults to 6",
		type=int,
		default=6
	)
	
	argp.add_argument(
		"input_file",
		help="VSPAERO .history file",
	)
	
	args = argp.parse_args()
	
	cases = get_cases(args.input_file)
	print_table(cases, args.coeff, args.indentation, args.precision)


#!/usr/bin/env python
#-*- coding:utf-8 -*-

import argparse
import os, sys
import math

import scipy.interpolate

from fgtools.utils.interpolator import Interpolator
from fgtools.utils import range

class Case:
	def __init__(self, textcase):
		textcase.pop(0) # get rid of the Name Value Unit legend line
		self.Sref = float(textcase.pop(0)[1].split()[1])
		self.Bref = float(textcase.pop(0)[1].split()[1])
		self.Cref = float(textcase.pop(0)[1].split()[1])
		self.Xcg = float(textcase.pop(0)[1].split()[1])
		self.Ycg = float(textcase.pop(0)[1].split()[1])
		self.Zcg = float(textcase.pop(0)[1].split()[1])
		self.Mach = float(textcase.pop(0)[1].split()[1])
		self.AoA = float(textcase.pop(0)[1].split()[1])
		self.Beta = float(textcase.pop(0)[1].split()[1])
		self.Rho = float(textcase.pop(0)[1].split()[1])
		self.Vinf = float(textcase.pop(0)[1].split()[1])
		self.RollRate = float(textcase.pop(0)[1].split()[1])
		self.PitchRate = float(textcase.pop(0)[1].split()[1])
		self.YawRate = float(textcase.pop(0)[1].split()[1])
		textcase.pop(0) # get rid of the Solver case line
		legend = textcase.pop(0)
		
		coeffmap = {i: k for i, k in enumerate(legend[1].split()[4:])}
		self.coeffs = {k: None for k in coeffmap.values()}
		
		line = (-1, "")
		while True:
			tline = textcase.pop(0)
			if "Skin Friction Drag Break Out:" in tline:
				break
			line = tline
		
		coeffs = line[1].split()[4:]
		if len(coeffs) > 0:
			for i, coeff in enumerate(coeffs):
				if "nan" in coeff:
					coeff = math.nan
				elif "inf" in coeff:
					coeff = math.inf
				else:
					coeff = float(coeff)
				self.coeffs[coeffmap[i]] = coeff
		else:
			raise ValueError(f"found no coefficients at line {line[0]}")
	
	def __str__(self):
		return "Case(" + ", ".join(str(k) + " = " + str(v) for k, v in vars(self).items()) + ")"
	
	def __repr__(self):
		return self.__str__()

def get_cases(path, mach):
	path = os.path.abspath(path)
	
	if not path.endswith(".history"):
		print("The specified file", path, "is not a VSPAERO .history file - exiting")
		sys.exit(1)
	
	textcases = []
	textcase = []
	cases = {}
	
	with open(path, "r") as histf:
		lines = histf.readlines()[1:]
		for lineno, line in enumerate(lines):
			if line.startswith("****"):
				textcases.append(textcase)
				textcase = []
				continue
			if line.strip():
				textcase.append((lineno, line.strip()))
		textcases.append(textcase)
		
		for textcase in textcases:
			case = Case(textcase)
			if case.RollRate or case.YawRate or case.PitchRate or case.Mach != mach:
				continue
			if not case.AoA in cases:
				cases[case.AoA] = {}
			cases[case.AoA][case.Beta] = case
	
	mostbetas = len(max(cases.values(), key=lambda d: len(d)))
	for AoA in list(cases.keys()):
		if len(cases[AoA]) < mostbetas:
			del cases[AoA]
			continue
	
	return cases

def get_raw_coeffs(cases, coeff):
	coeffs = {}
	for AoA in cases:
		for Beta in cases[AoA]:
			if not coeff in cases[AoA][Beta].coeffs:
				print("The coefficient", coeff, "does not exist in the specified .history file - exiting")
				sys.exit(1)
			
			if not AoA in coeffs:
				coeffs[AoA] = {}
			coeffs[AoA][Beta] = cases[AoA][Beta].coeffs[coeff]
	return coeffs

def get_interpolated_coeffs(cases, coeff, alphas, betas, symmetrize):
	coeffs = get_raw_coeffs(cases, coeff)
	ralphas = list(coeffs.keys())
	rbetas = list(coeffs[ralphas[0]].keys())
	values = list([list(coeffs[ralpha].values()) for ralpha in ralphas])
	interp = scipy.interpolate.RectBivariateSpline(ralphas, rbetas, values)
	#interp = scipy.interpolate.interp2d(rbetas, ralphas, values, fill_value=None)
	coeffs = {}
	for i, alpha in enumerate(alphas):
		if not alpha in coeffs:
			coeffs[alpha] = {}
		for j, beta in enumerate(betas):
			if symmetrize:
				s = interp(alpha, beta, grid=False)
				coeffs[alpha][beta] = math.copysign((abs(interp(alpha, beta, grid=False)) + abs(interp(alpha, -beta, grid=False))) / 2, s)
			else:
				coeffs[alpha][beta] = interp(alpha, beta, grid=False)
			#coeffs[alpha][beta] = interp([beta], [alpha])
	return coeffs
	
def print_table(coeffs, indent, precision, use_wing_alpha):
	print("<table>")
	print(indent + '<independentVar lookup="row">aero/alpha-' + ("wing-" if use_wing_alpha else "") + 'deg</independentVar>')
	if len(coeffs[list(coeffs.keys())[0]]) > 1:
		print(indent + '<independentVar lookup="column">aero/beta-deg</independentVar>')
	#print(indent + '<independentVar lookup="table">velocities/mach</independentVar>')
	print(indent + "<tableData>")
	if len(coeffs[list(coeffs.keys())[0]]) > 1:
		print(indent + indent + indent + indent + (indent + indent).join(map(str, coeffs[list(coeffs.keys())[0]].keys())))
	for AoA in coeffs:
		print(indent + indent + str(AoA), end="")
		for Beta in coeffs[AoA]:
			print(indent + ("%." + str(precision) + "f") % coeffs[AoA][Beta], end="")
		print()
	print(indent + "</tableData>")
	print("</table>")


def main():
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
		"--alpha-min",
		help="Lowest alpha table lookup value",
		type=float,
		default=None
	)
	argp.add_argument(
		"--alpha-max",
		help="Highest alpha table lookup value",
		type=float,
		default=None
	)
	argp.add_argument(
		"--alpha-step",
		help="Alpha table lookup value step size",
		type=float,
		default=None
	)
	
	argp.add_argument(
		"--beta-min",
		help="Lowest alpha table lookup value",
		type=float,
		default=None
	)
	argp.add_argument(
		"--beta-max",
		help="Highest alpha table lookup value",
		type=float,
		default=None
	)
	argp.add_argument(
		"--beta-step",
		help="Alpha table lookup value step size",
		type=float,
		default=None
	)
	
	argp.add_argument(
		"-s", "--symmetrize",
		help="Symmetrize table around the sideslip axis",
		action="store_true",
	)
	
	argp.add_argument(
		"-w", "--use-wing-alpha",
		help="Use aero/alpha-wing-deg instead of aero/alpha-deg for the alpha lookup property",
		action="store_true"
	)
	
	argp.add_argument(
		"input_file",
		help="VSPAERO .history file",
	)
	
	argp.add_argument(
		"-m", "--mach",
		help="Mach for which to output table - must exist in the .history file !",
		type=float,
		required=True
	)
	
	argp.add_argument(
		"-C", "--list-coefficients",
		help="List coefficients defined in the input .history file",
		action="store_true",
	)
	
	args = argp.parse_args()
	
	cases = get_cases(args.input_file, args.mach)
	
	if args.list_coefficients:
		print("\t".join(list(list(cases.values())[0].values())[0].coeffs.keys()))
		sys.exit(0)
	
	if None not in (args.alpha_min, args.alpha_max, args.alpha_step, args.beta_min, args.beta_max, args.beta_step):
		alphas = list(range(args.alpha_min, args.alpha_max, args.alpha_step))
		alphas.append(args.alpha_max)
		betas = list(range(args.beta_min, args.beta_max, args.beta_step))
		betas.append(args.beta_max)
		coeffs = get_interpolated_coeffs(cases, args.coeff, alphas, betas, args.symmetrize)
	else:
		coeffs = get_raw_coeffs(cases, args.coeff)
	print_table(coeffs, args.indentation, args.precision, args.use_wing_alpha)

if __name__ == '__main__':
	main()


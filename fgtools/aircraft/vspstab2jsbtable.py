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
		self.Sref = float(textcase.pop(0).split()[1])
		self.Bref = float(textcase.pop(0).split()[1])
		self.Cref = float(textcase.pop(0).split()[1])
		self.Xcg = float(textcase.pop(0).split()[1])
		self.Ycg = float(textcase.pop(0).split()[1])
		self.Zcg = float(textcase.pop(0).split()[1])
		self.Mach = float(textcase.pop(0).split()[1])
		self.Alpha = float(textcase.pop(0).split()[1])
		self.Beta = float(textcase.pop(0).split()[1])
		self.Rho = float(textcase.pop(0).split()[1])
		self.Vinf = float(textcase.pop(0).split()[1])
		self.RollRate = float(textcase.pop(0).split()[1])
		self.PitchRate = float(textcase.pop(0).split()[1])
		self.YawRate = float(textcase.pop(0).split()[1])
		textcase.pop(0) # get rid of the Solver case line
		textcase.pop(0) # get rid of another legend line
		
		firstrowindex = -99999
		axeslineindex = -99999
		for i, line in enumerate(textcase):
			if line.startswith("CFx"):
				firstrowindex = i
			elif line.startswith("Coef"):
				axeslineindex = i
		if firstrowindex == -99999:
			print("Error: malformed .stab file: missing CFx line in case")
			sys.exit(1)
		if axeslineindex == -99999:
			print("Error: malformed .stab file: missing axes legend line in case")
			sys.exit(1)
		
		axes = textcase[axeslineindex].split()
		
		textcase = textcase[firstrowindex:]
		
		self.data = {}
		
		for i in range(11):
			line = textcase.pop(0).split()
			self.data[line[0]] = {axes[i]: float(line[i]) for i in range(1, len(axes) - 1)}
	
	def __str__(self):
		return "Case(" + ", ".join(str(k) + " = " + str(v) for k, v in vars(self).items()) + ")"
	
	def __repr__(self):
		return self.__str__()

def get_cases(path, mach):
	path = os.path.abspath(path)
	
	if not path.endswith(".stab"):
		print("The specified file", path, "is not a VSPAERO .stab file - exiting")
		sys.exit(1)
	
	with open(path, "r") as stabf:
		textcases = []
		lines = stabf.readlines()[1:]
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
			if case.Mach != mach:
				continue
			if not case.Alpha in cases:
				cases[case.Alpha] = {}
			cases[case.Alpha][case.Beta] = case
	
	mostbetas = len(max(cases.values(), key=lambda d: len(d)))
	for Alpha in list(cases.keys()):
		if len(cases[Alpha]) < mostbetas:
			del cases[Alpha]
			continue
	
	return cases

def get_raw_coeffs(cases, axis, coeff):
	coeffs = {}
	for Alpha in cases:
		for Beta in cases[Alpha]:
			if not coeff in cases[Alpha][Beta].data.keys():
				print("The coefficient", coeff, "does not exist in the specified .stab file - exiting")
				sys.exit(1)
			if not axis in cases[Alpha][Beta].data[coeff].keys():
				print("The axis", axis, "does not exist in the specified .stab file - exiting")
				sys.exit(1)
			
			if not Alpha in coeffs:
				coeffs[Alpha] = {}
			coeffs[Alpha][Beta] = cases[Alpha][Beta].data[coeff][axis]
	return coeffs

def get_interpolated_coeffs(cases, axis, coeff, alphas, betas, symmetrize):
	coeffs = get_raw_coeffs(cases, axis, coeff)
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
	for Alpha in coeffs:
		print(indent + indent + str(Alpha), end="")
		for Beta in coeffs[Alpha]:
			print(indent + ("%." + str(precision) + "f") % coeffs[Alpha][Beta], end="")
		print()
	print(indent + "</tableData>")
	print("</table>")


def main():
	argp = argparse.ArgumentParser(description="vsphist2jsbtable.py - Takes a VSPAERO .history file and a coefficient as input and outputs a JSBSim interpolation table for that coefficient from the VSPAERO cases")
	
	argp.add_argument(
		"-a", "--axis",
		help="Name of the axis to produce a table for",
		required=True,
	)
	
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
	
	args = argp.parse_args()
	
	cases = get_cases(args.input_file, args.mach)
	if None not in (args.alpha_min, args.alpha_max, args.alpha_step, args.beta_min, args.beta_max, args.beta_step):
		alphas = list(range(args.alpha_min, args.alpha_max, args.alpha_step))
		alphas.append(args.alpha_max)
		betas = list(range(args.beta_min, args.beta_max, args.beta_step))
		betas.append(args.beta_max)
		coeffs = get_interpolated_coeffs(cases, args.axis, args.coeff, alphas, betas, args.symmetrize)
	else:
		coeffs = get_raw_coeffs(cases, args.axis, args.coeff)
	print_table(coeffs, args.indentation, args.precision, args.use_wing_alpha)

if __name__ == '__main__':
	main()




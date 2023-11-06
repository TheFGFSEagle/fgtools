#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os, sys
import argparse
import re
import requests
import subprocess
import shlex

from PIL import Image

from fgtools.utils import constants

pattern = r'(?<=src=")https:\/\/static-repo.emanualonline.com\/.+\.jpg(?=")'

def download_pages(url, output, resume):
	html = requests.get(url).text
	urls = re.findall(pattern, html)
	urltemplate = "/".join(urls[0].split("/")[:-2] + ["%d", "%d.jpg"])
	
	paths = []
	i = 1
	if resume:
		paths = list(map(lambda s: os.path.join(constants.CACHEDIR, s), filter(lambda s: s.endswith(".jpg"), os.listdir(constants.CACHEDIR))))
		paths = sorted(paths, key=lambda s: int(s.split("-")[-1].split(".")[0]))[:-1]
		if len(paths):
			i = int(paths[-1].split("-")[-1].split(".")[0])
	
	while True:
		page = requests.get(urltemplate % (i, i))
		i += 1
		if page.status_code != 200:
			break
		
		path = os.path.join(constants.CACHEDIR, os.path.split(output)[-1] + f"-{i}.jpg")
		paths.append(path)
		with open(path, "wb") as f:
			f.write(page.content)
	
	return paths

def write_pdf(paths, output, keep):
	print(f"Joining {len(paths)} JPG files into {output} … ", end="")
	newpaths = " ".join([f'"{path}"' for path in paths])
	subprocess.run(args=shlex.split(f'img2pdf {newpaths} --output "{output}"'))
	print("done.")
	if keep:
		return
	print("Deleting JPG files … ", end="")
	for path in paths:
		os.remove(path)
	print("done")

def main()
	argp = argparse.ArgumentParser()
	
	argp.add_argument(
		"url",
		help="URL to emanualonline.com PDF offer"
	)
	
	argp.add_argument(
		"-o", "--output",
		help="Output file",
		required=True
	)
	
	argp.add_argument(
		"-r", "--resume",
		help="Resume interrupted download",
		action="store_true"
	)
	
	argp.add_argument(
		"-k", "--keep",
		help="Keep cached pages after joining (for debugging)",
		action="store_true"
	)
	
	args = argp.parse_args()
	
	os.makedirs(os.path.join(*os.path.split(os.path.relpath(args.output))[:-1]) or ".", exist_ok=True)
	
	paths = download_pages(args.url, args.output, args.resume)
	write_pdf(paths, args.output, args.keep)

if __name__ == '__main__':
	main()




#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import argparse
import re
import requests

from fgtools.utils import constants

pattern = r'(?<=src=")https:\/\/static-repo.emanualonline.com\/.+\.jpg(?=")'

def download_pages(url, output):
	html = requests.get(url).text
	urls = re.findall(pattern, html)
	urltemplate = "/".join(urls[0].split("/")[:-2] + ["%d", "%d.jpg"])
	
	paths = []
	i = 1
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

def write_pdf(paths, output):
	print(f"Joining {len(paths)} JPG files into {output} … ", end="")
	newpaths = " ".join([f'"{path}"' for path in paths])
	os.system(f'img2pdf {newpaths} --output "{output}"')
	print("done.")
	print("Deleting JPG files … ", end="")
	for path in paths:
		os.remove(path)
	print("done")

if __name__ == "__main__":
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
	
	args = argp.parse_args()
	
	os.makedirs(os.path.join(*os.path.split(os.path.relpath(args.output))[:-1]) or ".", exist_ok=True)
	
	paths = download_pages(args.url, args.output)
	write_pdf(paths, args.output)


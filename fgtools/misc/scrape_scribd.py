#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import argparse
import re
import requests

from PIL import Image

from bs4 import BeautifulSoup

from fgtools.utils import constants
json_pattern = r'(?<=content-url: ")https:\/\/html.scribdassets.com\/.+\.jsonp(?=")'
img_pattern = r'<img .+?\/>'

class JSPage:
	def __init__(self, number, width, height, url):
		self.number = number
		self.width = width
		self.height = height
		self.url = url
	
	def get_image(self):
		text = requests.get(self.url).text
		images = list(map(lambda s: BeautifulSoup(s.replace("\\", ""), features="lxml").body.find("img"), re.findall(img_pattern, text)))
		if not images:
			return None
		src_image = Image.open(requests.get(images[0]["orig"], stream=True).raw)
		pil_image = Image.new("RGB", (self.width, self.height))
		pil_image.paste((255, 255, 255), (0, 0, pil_image.size[0], pil_image.size[1]))
		for image in images:
			style = {}
			for item in image["style"].split(";"):
				item = item.split(":")
				style[item[0]] = item[1].replace("px", "")
			
			clip = style["clip"]
			clip = {k: int(v) for k, v in zip(("top", "right", "bottom", "left"), clip[clip.find("(") + 1:-1].split(" "))}
			cropped_src_image = src_image.copy().crop((clip["left"], clip["top"], clip["right"], clip["bottom"]))
			pil_image.paste(cropped_src_image, (int(style["left"]) + clip["left"], int(style["top"]) + clip["top"]))
		
		return pil_image

def parse_pages_script(script):
	lines = list(map(str.strip, script.split("\n")[1:-1]))
	number = 0
	width = 0
	height = 0
	url = ""
	pages = []
	for line in lines:
		if "pageNum" in line:
			number = int(line.split(": ")[1][:-1])
		elif "origWidth" in line:
			width = int(line.split(": ")[1][:-1])
		elif "origHeight" in line:
			height = int(line.split(": ")[1][:-1])
		elif "contentUrl" in line:
			url = line.split(": ")[1][1:-1]
		
		if number and width and height and url:
			page = JSPage(number, width, height, url)
			pages.append(page)
			number = width = height = 0
			url = ""
	
	return pages

def download_pages(url, output):
	html = BeautifulSoup(requests.get(url).text, features="lxml")
	pages_script = html.body.find("div", attrs={"class": "outer_page_container"}).find("script", attrs={"type": "text/javascript"})
	pages = sorted(parse_pages_script(str(pages_script)), key=lambda p: p.number)
	
	paths = []
	for i, page in enumerate(pages):
		print(f"Downloading page {i} of {len(pages)}", end="\r")
		path = os.path.join(constants.CACHEDIR, os.path.split(output)[-1] + f"-{page.number}.jpg")
		image = page.get_image()
		if image:
			paths.append(path)
			image.save(path, "JPEG")
	print()
	
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

def main():
	argp = argparse.ArgumentParser()
	
	argp.add_argument(
		"url",
		help="URL to Scribd web page"
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

if __name__ == '__main__':
	main()




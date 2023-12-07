#!/usr/bin/env python
#-*- coding:utf-8 -*-

import logging

logger = logging.getLogger("fgtools")
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_logger():
	return logging.getLogger("fgtools")


#!/usr/bin/env python
#-*- coding:utf-8 -*-

import struct
import typing

def _read(f: typing.BinaryIO, format_str: str):
	size = struct.calcsize(format_str)
	b = f.read(size)
	if len(b) != size:
		print(f"binary._read: calculated size {size}, actual size {len(b)}")
	return struct.unpack(format_str, b)[0]

def read_int(f: typing.BinaryIO):
	return _read(f, "<i")

def read_uint(f: typing.BinaryIO):
	return _read(f, "<I")

def read_short(f: typing.BinaryIO):
	return _read(f, "<h")

def read_ushort(f: typing.BinaryIO):
	return _read(f, "<H")

def read_double(f: typing.BinaryIO):
	return _read(f, "<d")

def read_float(f: typing.BinaryIO):
	return _read(f, "<f")

def read_char(f: typing.BinaryIO):
	return _read(f, "<c")

def read_byte(f: typing.BinaryIO):
	return _read(f, f"<b")

def read_bytes(f: typing.BinaryIO, length: int):
	return _read(f, f"<{length}s")

def _write(f: typing.BinaryIO, format_str: str, value: typing.Any):
	size = struct.calcsize(format_str)
	b = struct.pack(format_str, value)
	written_len = f.write(b)
	if written_len != size:
		print(f"binary._write: calculated size {size}, actual size {written_len}")
	return written_len

def write_int(f: typing.BinaryIO, value: int):
	return _write(f, "<i", value)

def write_uint(f: typing.BinaryIO, value: int):
	return _write(f, "<I", value)

def write_short(f: typing.BinaryIO, value: int):
	return _write(f, "<h", value)

def write_ushort(f: typing.BinaryIO, value: int):
	return _write(f, "<H", value)

def write_double(f: typing.BinaryIO, value: float):
	return _write(f, "<d", value)

def write_float(f: typing.BinaryIO, value: float):
	return _write(f, "<f", value)

def write_char(f: typing.BinaryIO, value: str):
	return _write(f, "<c", value)

def write_byte(f: typing.BinaryIO, value: str):
	return _write(f, f"<b", value)

def write_bytes(f: typing.BinaryIO, value: str):
	length = len(value)
	return _write(f, f"<{length}s", value)

def size_int():
	return struct.calcsize("<i")

def size_uint():
	return struct.calcsize("<I")

def size_short():
	return struct.calcsize("<h")

def size_ushort():
	return struct.calcsize("<H")

def size_double():
	return struct.calcsize("<d")

def size_float():
	return struct.calcsize("<f")

def size_char():
	return struct.calcsize("<c")

def size_byte():
	return struct.calcsize("<b")

def size_bytes(length: int):
	return struct.calcsize(f"<{length}s")

def bit_count(num: int, val: bool=True):
	return bin(num).count(str(int(val)))


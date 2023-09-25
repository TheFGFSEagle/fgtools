#!/usr/bin/env python
#-*- coding:utf-8 -*-

import gzip
import typing
import os
import enum
import numbers
import io
import time

from plum import dispatch

from fgtools.utils import binary
from fgtools.geo import Coord

class NotABtgFileError(Exception):
	def __init__(self, path):
		self.path = path
		Exception.__init__(self, f"{path} does not seem to be a BTG file")

class BTGFormatError(Exception):
	def __init__(self, path, cause):
		self.path = path
		self.cause = cause
		Exception.__init__(self, f"{path}: {cause}")

class BTGObjectTypes(enum.IntEnum):
	BOUNDING_SPHERE = 0
	VERTEX_LIST = 1
	NORMAL_LIST = 2
	TEXCOORD_LIST = 3
	COLOR_LIST = 4
	VA_FLOAT_LIST = 5
	VA_INTEGER_LIST = 6
	POINTS = 9
	TRIANGLE_FACES = 10
	TRIANGLE_STRIPS = 11
	TRIANGLE_FANS = 12

class BTGIndexTypes(enum.IntEnum):
	VERTICES = 0x01
	NORMALS = 0x02
	COLORS = 0x04
	TEXCOORDS_0 =0x08
	TEXCOORDS_1 = 0x10
	TEXCOORDS_2 = 0x20
	TEXCOORDS_3 = 0x40

class BTGVertextAttributeTypes(enum.IntEnum):
	INTEGER_0 = 0x00000001
	INTEGER_1 = 0x00000002
	INTEGER_2 = 0x00000004
	INTEGER_3 = 0x00000008
	FLOAT_0 =   0x00000100
	FLOAT_1 =   0x00000200
	FLOAT_2 =   0x00000400
	FLOAT_3 =   0x00000800

class BTGPropertyTypes(enum.IntEnum):
	MATERIAL = 0
	INDEX_MASK  = 1
	VERTEX_ATTRIBUTE_MASK = 2

class BTGElement:
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		self.num_bytes = binary.read_uint(f)
		self.bytes = io.BytesIO(f.read(self.num_bytes))
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		pass

class BTGObject(BTGElement):
	@dispatch
	def __init__(self, element_class, object_type):
		BTGElement.__init__(self)
		self.element_class = element_class
		self.element_args = []
		self.object_type = object_type
		self.properties = {}
		self.elements = []
	
	@dispatch
	def __init__(self, element_class, element_args, object_type):
		BTGElement.__init__(self)
		self.element_class = element_class
		self.element_args = element_args
		self.object_type = object_type
		self.properties = {}
		self.elements = []
	
	@dispatch
	def __init__(self, element_class, object_type, properties, elements):
		BTGElement.__init__(self)
		self.element_class = element_class
		self.element_args = []
		self.object_type = object_type
		self.properties = properties
		self.elements = elements
	
	@dispatch
	def __init__(self, element_class, element_args, object_type, properties, elements):
		BTGElement.__init__(self)
		self.element_class = element_class
		self.element_args = element_args
		self.object_type = object_type
		self.properties = properties
		self.elements = elements
	
	def _read_properties(self, f: typing.BinaryIO, num_properties: int):
		for i in range(num_properties):
			try:
				prop_type_raw = binary.read_char(f)
				prop_type = BTGPropertyTypes(ord(prop_type_raw))
			except ValueError:
					raise BTGFormatError(f"Unknown / malformed property type {prop_type_raw}")
			prop_data_length = binary.read_uint(f)
			prop_data = binary.read_bytes(f, prop_data_length)
			self.properties[prop_type] = prop_data
	
	def _read_elements(self, reader: "ReaderWriterBTG", f: typing.BinaryIO, num_elements: int):
		for i in range(num_elements):
			element = self.element_class(*self.element_args)
			element.read(reader, f)
			self.elements.append(element)
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		if reader.version >= 10:
			num_properties = binary.read_uint(f)
			num_elements = binary.read_uint(f)
		elif reader.version >= 7:
			num_properties = binary.read_ushort(f)
			num_elements = binary.read_ushort(f)
		else:
			num_properties = binary.read_short(f)
			num_elements = binary.read_short(f)
		self._read_properties(f, num_properties)
		self._read_elements(reader, f, num_elements)
	
	def _write_properties(self, f: typing.BinaryIO):
		for prop_type in self.properties:
			binary.write_char(f, chr(prop_type).encode("ascii"))
			binary.write_uint(f, len(self.properties[prop_type]))
			binary.write_bytes(f, self.properties[prop_type])
	
	def _write_elements(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		for element in self.elements:
			element.write(writer, f)
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		if writer.version >= 10:
			fwrite = binary.write_uint
		elif writer.version >= 7:
			fwrite = binary.write_ushort
		else:
			fwrite = binary.write_short
		
		fwrite(f, len(self.properties))
		fwrite(f, len(self.elements))
		self._write_properties(f)
		self._write_elements(writer, f)

class BTGGeometryObject(BTGObject):
	def __init__(self, element_class, object_type):
		BTGObject.__init__(self, element_class, object_type)
		self.element_class = element_class
		self.material = ""
		self.index_mask = BTGIndexTypes.VERTICES
		if element_class != BTGGeometryElementPoint:
			self.index_mask = BTGIndexTypes(BTGIndexTypes.TEXCOORDS_0.value)
		self.vertex_attribute_mask = 0
	
	def _read_properties(self, f: typing.BinaryIO, num_properties: int):
		BTGObject._read_properties(self, f, num_properties)
		if BTGPropertyTypes.MATERIAL in self.properties:
			self.material = self.properties[BTGPropertyTypes.MATERIAL]
		if BTGPropertyTypes.INDEX_MASK in self.properties:
			self.index_mask = int.from_bytes(self.properties[BTGPropertyTypes.INDEX_MASK], "little")
		if BTGPropertyTypes.VERTEX_ATTRIBUTE_MASK in self.properties:
			self.vertex_attribute_mask = int.from_bytes(self.properties[BTGPropertyTypes.VERTEX_ATTRIBUTE_MASK], "little")
		
		if not self.index_mask:
			raise ValueError(f"index mask has no bits set")
	
	def _read_elements(self, reader: "ReaderWriterBTG", f: typing.BinaryIO, num_elements: int):
		for i in range(num_elements):
			element = self.element_class(*self.element_args)
			element.read(reader, f, self)
			self.elements.append(element)
	
	def _write_properties(self, f: typing.BinaryIO):
		self.properties = {}
		self.properties[BTGPropertyTypes.MATERIAL] = self.material
		
		self.index_mask = 0
		if self.elements[0].vertex_indices:
			self.index_mask |= BTGIndexTypes.VERTICES
		if self.elements[0].normal_indices:
			self.index_mask |= BTGIndexTypes.NORMALS
		if self.elements[0].color_indices:
			self.index_mask |= BTGIndexTypes.COLORS
		if self.elements[0].tex_coord_indices[0]:
			self.index_mask |= BTGIndexTypes.TEXCOORDS_0
		if self.elements[0].tex_coord_indices[1]:
			self.index_mask |= BTGIndexTypes.TEXCOORDS_1
		if self.elements[0].tex_coord_indices[2]:
			self.index_mask |= BTGIndexTypes.TEXCOORDS_2
		if self.elements[0].tex_coord_indices[3]:
			self.index_mask |= BTGIndexTypes.TEXCOORDS_3
		
		self.properties[BTGPropertyTypes.INDEX_MASK] = chr(self.index_mask).encode("ascii")
		
		self.vertex_attribute_indices = 0
		if self.elements[0].vertex_attribute_indices[0]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.INTEGER_0
		if self.elements[0].vertex_attribute_indices[1]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.INTEGER_1
		if self.elements[0].vertex_attribute_indices[2]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.INTEGER_2
		if self.elements[0].vertex_attribute_indices[3]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.INTEGER_3
		if self.elements[0].vertex_attribute_indices[4]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.FLOAT_0
		if self.elements[0].vertex_attribute_indices[5]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.FLOAT_1
		if self.elements[0].vertex_attribute_indices[6]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.FLOAT_2
		if self.elements[0].vertex_attribute_indices[7]:
			self.vertex_attribute_mask |= BTGVertextAttributeTypes.FLOAT_3
		
		if self.vertex_attribute_mask:
			self.properties[BTGPropertyTypes.VERTEX_ATTRIBUTE_MASK] = bytes(self.vertex_attribute_mask)
		
		BTGObject._write_properties(self, f)

	def _write_elements(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		for element in self.elements:
			element.write(writer, f, self)
	
class BTGBoundingSphereElement(BTGElement):
	@dispatch
	def __init__(self):
		BTGElement.__init__(self)
		self.x = self.y = self.z = self.radius = None
	
	@dispatch
	def __init__(self, x: float, y: float, z: float, radius: float):
		BTGElement.__init__(self)
		self.x = x
		self.y = y
		self.z = z
		self.radius = radius
	
	def __repr__(self):
		return f"BoundingSphere(x={self.x}, y={self.y}, z={self.z}, radius={self.radius})"
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		BTGElement.read(self, reader, f)
		self.x = binary.read_double(self.bytes)
		self.y = binary.read_double(self.bytes)
		self.z = binary.read_double(self.bytes)
		self.radius = binary.read_float(self.bytes)
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		BTGElement.write(self, writer, f)
		binary.write_uint(f, binary.size_double() * 3 + binary.size_float())
		binary.write_double(f, self.x)
		binary.write_double(f, self.y)
		binary.write_double(f, self.z)
		binary.write_float(f, self.radius)

class BTGListElement(BTGElement):
	@dispatch
	def __init__(self, item_class):
		BTGElement.__init__(self)
		self.items = []
		self.item_class = item_class
	
	@dispatch
	def __init__(self, item_class, items):
		BTGElement.__init__(self)
		self.items = items
		self.item_class = item_class
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		BTGElement.read(self, reader, f)
		item_count = self.num_bytes // self.item_class.bytes_size
		for i in range(item_count):
			item = self.item_class()
			item.read(reader, self.bytes)
			self.items.append(item)
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		BTGElement.write(self, writer, f)
		binary.write_uint(f, self.item_class.bytes_size * len(self.items))
		for item in self.items:
			item.write(writer, f)

class BTGListElementItem(BTGElement):
	bytes_size = 1

class BTGListElementVertexItem(BTGListElementItem):
	bytes_size = binary.size_float() * 3
	@dispatch
	def __init__(self):
		BTGListElementItem.__init__(self)
		self.x = self.y = self.z = None
		self.coord = None
	
	@dispatch
	def __init__(self, x: numbers.Real, y: numbers.Real, z: numbers.Real):
		BTGListElementItem.__init__(self)
		self.x = x
		self.y = y
		self.z = z
		self.coord = Coord.from_cartesian(self.x, self.y, self.z)
	
	@dispatch
	def set(self, lon: numbers.Real, lat: numbers.Real, alt: numbers.Real):
		self.coord = Coord(lon, lat, alt)
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		self.x = reader.bs.elements[0].x + binary.read_float(f)
		self.y = reader.bs.elements[0].y + binary.read_float(f)
		self.z = reader.bs.elements[0].z + binary.read_float(f)
		self.coord = Coord.from_cartesian(self.x, self.y, self.z)
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		binary.write_float(f, self.x - writer.bs.elements[0].x)
		binary.write_float(f, self.y - writer.bs.elements[0].y)
		binary.write_float(f, self.z - writer.bs.elements[0].z)

class BTGListElementColorItem(BTGListElementItem):
	bytes_size = binary.size_float() * 4
	@dispatch
	def __init__(self):
		BTGListElementItem.__init__(self)
		self.r = self.g = self.b = self.a = None
	
	@dispatch
	def __init__(self, r: numbers.Real, g: numbers.Real, b: numbers.Real, a: numbers.Real):
		BTGListElementItem.__init__(self)
		self.r = r
		self.g = g
		self.b = b
		self.a = a
	
	def set(self, r: numbers.Real, g: numbers.Real, b: numbers.Real, a: numbers.Real):
		self.r = r
		self.g = g
		self.b = b
		self.a = a
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		self.r = binary.read_float(f)
		self.g = binary.read_float(f)
		self.b = binary.read_float(f)
		self.a = binary.read_float(f)
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		binary.write_float(f, self.r)
		binary.write_float(f, self.g)
		binary.write_float(f, self.b)
		binary.write_float(f, self.a)

class BTGListElementNormalItem(BTGListElementItem):
	bytes_size = binary.size_byte() * 3
	@dispatch
	def __init__(self):
		BTGListElementItem.__init__(self)
		self.x = self.y = self.z = None
	
	@dispatch
	def __init__(self, x: numbers.Real, y: numbers.Real, z: numbers.Real):
		BTGListElementItem.__init__(self)
		self.x = x
		self.y = y
		self.z = z
	
	def set(self, x: numbers.Real, y: numbers.Real, z: numbers.Real):
		self.x = x
		self.y = y
		self.z = z
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		self.x = binary.read_byte(f) / 127.5 - 1.0
		self.y = binary.read_byte(f) / 127.5 - 1.0
		self.z = binary.read_byte(f) / 127.5 - 1.0
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		binary.write_byte(f, int((self.x + 1.0) * 127.5))
		binary.write_byte(f, int((self.y + 1.0) * 127.5))
		binary.write_byte(f, int((self.z + 1.0) * 127.5))

class BTGListElementTexCoordItem(BTGListElementItem):
	bytes_size = binary.size_float() * 2
	@dispatch
	def __init__(self):
		BTGListElementItem.__init__(self)
		self.u = self.v = None
	
	@dispatch
	def __init__(self, u: numbers.Real, v: numbers.Real):
		BTGListElementItem.__init__(self)
		self.u = u
		self.v = v
	
	def set(self, u: numbers.Real, v: numbers.Real):
		self.u = u
		self.v = v
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		self.u = binary.read_float(f)
		self.v = binary.read_float(f)

	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		binary.write_float(f, self.u)
		binary.write_float(f, self.v)

class BTGListElementVAIntegerItem(BTGListElementItem):
	bytes_size = binary.size_int()
	@dispatch
	def __init__(self):
		BTGListElementItem.__init__(self)
		self.value = None
	
	@dispatch
	def __init__(self, value: numbers.Real):
		BTGListElementItem.__init__(self)
		self.value = value
	
	def set(self, value: numbers.Real):
		self.value = value
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		self.value = binary.read_int(f)

	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		binary.write_int(f, self.value)

class BTGListElementVAFloatItem(BTGListElementItem):
	bytes_size = binary.size_float()
	@dispatch
	def __init__(self):
		BTGListElementItem.__init__(self)
		self.value = None
	
	@dispatch
	def __init__(self, value: numbers.Real):
		BTGListElementItem.__init__(self)
		self.value = value
	
	def set(self, value: numbers.Real):
		self.value = value
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO):
		self.value = binary.read_float(f)
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO):
		binary.write_float(f, self.value)

class BTGGeometryElement(BTGElement):
	@dispatch
	def __init__(self):
		BTGElement.__init__(self)
		self.vertex_indices = []
		self.normal_indices = []
		self.color_indices = []
		self.tex_coord_indices = [[], [], [], []]
		self.vertex_attribute_indices = [[], [], [], [], [], [], [], []]
	
	@dispatch
	def __init__(self, vertex_indices, normal_indices, color_indices, tex_coord_indices, vertex_attribute_indices):
		BTGElement.__init__(self)
		self.vertex_indices = vertex_indices
		self.normal_indices = normal_indices
		self.color_indices = color_indices
		self.tex_coord_indices = tex_coord_indices
		self.vertex_attribute_indices = vertex_attribute_indices
	
	def read(self, reader: "ReaderWriterBTG", f: typing.BinaryIO, geom_object: BTGGeometryObject):
		BTGElement.read(self, reader, f)
		
		if reader.version >= 10:
			fsize = binary.size_uint
			fread = binary.read_uint
		else:
			fsize = binary.size_ushort
			fread = binary.read_ushort
		index_count = fsize() * binary.bit_count(geom_object.index_mask)
		vertex_attribute_count = fsize() * binary.bit_count(geom_object.vertex_attribute_mask)
		count = self.num_bytes // (index_count + vertex_attribute_count)
		
		for i in range(count):
			if geom_object.index_mask & BTGIndexTypes.VERTICES:
				self.vertex_indices.append(fread(self.bytes))
			if geom_object.index_mask & BTGIndexTypes.NORMALS:
				self.normal_indices.append(fread(self.bytes))
			if geom_object.index_mask & BTGIndexTypes.COLORS:
				self.color_indices.append(fread(self.bytes))
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_0:
				self.tex_coord_indices[0].append(fread(self.bytes))
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_1:
				self.tex_coord_indices[1].append(fread(self.bytes))
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_2:
				self.tex_coord_indices[2].append(fread(self.bytes))
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_3:
				self.tex_coord_indices[3].append(fread(self.bytes))
			if geom_object.vertex_attribute_mask:
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_0:
					self.vertex_attribute_indices[0].append(fread(self.bytes))
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_1:
					self.vertex_attribute_indices[1].append(fread(self.bytes))
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_2:
					self.vertex_attribute_indices[2].append(fread(self.bytes))
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_3:
					self.vertex_attribute_indices[3].append(fread(self.bytes))
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_0:
					self.vertex_attribute_indices[0].append(fread(self.bytes))
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_1:
					self.vertex_attribute_indices[1].append(fread(self.bytes))
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_2:
					self.vertex_attribute_indices[2].append(fread(self.bytes))
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_3:
					self.vertex_attribute_indices[3].append(fread(self.bytes))
	
	def write(self, writer: "ReaderWriterBTG", f: typing.BinaryIO, geom_object: BTGGeometryObject):
		BTGElement.write(self, writer, f)
		
		if writer.version >= 10:
			fsize = binary.size_uint
			fwrite = binary.write_uint
		else:
			fsize = binary.size_ushort
			fwrite = binary.write_ushort
		
		index_count = len(self.vertex_indices)
		size = fsize() * (binary.bit_count(geom_object.index_mask) + binary.bit_count(geom_object.vertex_attribute_mask))
		num_bytes = size * index_count
		fwrite(f, num_bytes)
		
		for i in range(len(self.vertex_indices)):
			fwrite(f, self.vertex_indices[i])
			if geom_object.index_mask & BTGIndexTypes.NORMALS:
				fwrite(f, self.normal_indices[i])
			if geom_object.index_mask & BTGIndexTypes.COLORS:
				fwrite(f, self.color_indices[i])
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_0:
				fwrite(f, self.tex_coord_indices[0][i])
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_1:
				fwrite(f, self.tex_coord_indices[1][i])
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_2:
				fwrite(f, self.tex_coord_indices[2][i])
			if geom_object.index_mask & BTGIndexTypes.TEXCOORDS_3:
				fwrite(f, self.tex_coord_indices[3][i])
			
			if geom_object.vertex_attribute_mask:
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_0:
					fwrite(f, self.vertex_attribute_indices[0][i])
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_1:
					fwrite(f, self.vertex_attribute_indices[1][i])
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_2:
					fwrite(f, self.vertex_attribute_indices[2][i])
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.INTEGER_3:
					fwrite(f, self.vertex_attribute_indices[3][i])
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_0:
					fwrite(f, self.vertex_attribute_indices[4][i])
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_1:
					fwrite(f, self.vertex_attribute_indices[5][i])
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_2:
					fwrite(f, self.vertex_attribute_indices[6][i])
				if geom_object.vertex_attribute_mask & BTGVertextAttributeTypes.FLOAT_3:
					fwrite(f, self.vertex_attribute_indices[7][i])

class BTGGeometryElementPoint(BTGGeometryElement):
	pass

class BTGGeometryElementTriangleFace(BTGGeometryElement):
	pass

class BTGGeometryElementTriangleFan(BTGGeometryElement):
	pass

class BTGGeometryElementTriangleStrip(BTGGeometryElement):
	pass

class ReaderWriterBTG:
	@dispatch
	def __init__(self):
		self.version = None
		self.creation_time = None
		self.num_objects = None
		self.path = None
		
		self.bs = BTGObject(BTGBoundingSphereElement, BTGObjectTypes.BOUNDING_SPHERE)
		self.vertex_list = BTGObject(BTGListElement, [BTGListElementVertexItem], BTGObjectTypes.VERTEX_LIST)
		self.color_list = BTGObject(BTGListElement, [BTGListElementColorItem], BTGObjectTypes.COLOR_LIST)
		self.normal_list = BTGObject(BTGListElement, [BTGListElementNormalItem], BTGObjectTypes.NORMAL_LIST)
		self.texcoord_list = BTGObject(BTGListElement, [BTGListElementTexCoordItem], BTGObjectTypes.TEXCOORD_LIST)
		self.va_integer_list = BTGObject(BTGListElement, [BTGListElementVAIntegerItem], BTGObjectTypes.VA_INTEGER_LIST)
		self.va_float_list = BTGObject(BTGListElement, [BTGListElementVAFloatItem], BTGObjectTypes.VA_FLOAT_LIST)
		self.points = []
		self.triangle_faces = []
		self.triangle_strips = []
		self.triangle_fans = []
	
	@dispatch
	def __init__(self, path: str):
		self.version = None
		self.creation_time = None
		self.num_objects = None
		self.path = path
		
		self.bs = BTGObject(BTGBoundingSphereElement, BTGObjectTypes.BOUNDING_SPHERE)
		self.vertex_list = BTGObject(BTGListElement, [BTGListElementVertexItem], BTGObjectTypes.VERTEX_LIST)
		self.color_list = BTGObject(BTGListElement, [BTGListElementColorItem], BTGObjectTypes.COLOR_LIST)
		self.normal_list = BTGObject(BTGListElement, [BTGListElementNormalItem], BTGObjectTypes.NORMAL_LIST)
		self.texcoord_list = BTGObject(BTGListElement, [BTGListElementTexCoordItem], BTGObjectTypes.TEXCOORD_LIST)
		self.va_integer_list = BTGObject(BTGListElement, [BTGListElementVAIntegerItem], BTGObjectTypes.VA_INTEGER_LIST)
		self.va_float_list = BTGObject(BTGListElement, [BTGListElementVAFloatItem], BTGObjectTypes.VA_FLOAT_LIST)
		self.points = []
		self.triangle_faces = []
		self.triangle_strips = []
		self.triangle_fans = []
		
		self.read(path)
	
	@dispatch
	def read(self):
		if self.path:
			self.read(self.path)
		else:
			raise RuntimeError("ReaderWriterBTG.read called without path and self.path is not set !")
	
	@dispatch
	def read(self, path: str):
		if not (path.endswith(".btg") or path.endswith(".btg.gz")):
			raise NotABtgFileError(path)
		if not os.path.isfile(path) and not path.endswith(".gz"):
			path += ".gz"
		if not os.path.isfile(path):
			raise FileNotFoundError(f"{path} does not exist")
		self.path = path
		
		fopen = gzip.open if path.endswith(".gz") else open
		with fopen(path, "rb") as f:
			header = binary.read_uint(f)
			if ((header & 0xFF000000) >> 24) == ord("S") and ((header & 0x00FF0000) >> 16) == ord("G"):
				self.version = header & 0x0000FFFF
			else:
				raise BTGFormatError(path, "Malformed header")
			
			self.creation_time = binary.read_uint(f)
			
			if self.version == 10:
				self.num_objects = binary.read_int(f)
			elif self.version == 7:
				self.num_objects = binary.read_ushort(f)
			else:
				self.num_objects = binary.read_short(f)
			
			for i in range(self.num_objects):
				try:
					object_type_raw = binary.read_char(f)
					object_type = BTGObjectTypes(ord(object_type_raw))
				except ValueError:
					raise BTGFormatError(f"Unknown / malformed object type: '{object_type_raw}'")
				
				if object_type == BTGObjectTypes.BOUNDING_SPHERE:
					self.bs.read(self, f)
				elif object_type == BTGObjectTypes.VERTEX_LIST:
					self.vertex_list.read(self, f)
				elif object_type == BTGObjectTypes.COLOR_LIST:
					self.color_list.read(self, f)
				elif object_type == BTGObjectTypes.NORMAL_LIST:
					self.normal_list.read(self, f)
				elif object_type == BTGObjectTypes.TEXCOORD_LIST:
					self.texcoord_list.read(self, f)
				elif object_type == BTGObjectTypes.VA_INTEGER_LIST:
					self.va_integer_list.read(self, f)
				elif object_type == BTGObjectTypes.VA_FLOAT_LIST:
					self.va_float_list.read(self, f)
				elif object_type == BTGObjectTypes.POINTS:
					points = BTGGeometryObject(
						BTGGeometryElementPoint,
						BTGObjectTypes.POINTS
					)
					points.read(self, f)
					self.points.append(points)
				elif object_type == BTGObjectTypes.TRIANGLE_FANS:
					triangle_fans = BTGGeometryObject(
						BTGGeometryElementTriangleFan,
						BTGObjectTypes.TRIANGLE_FANS
					)
					triangle_fans.read(self, f)
					self.triangle_fans.append(triangle_fans)
				elif object_type == BTGObjectTypes.TRIANGLE_STRIPS:
					triangle_strips = BTGGeometryObject(
						BTGGeometryElementTriangleStrip,
						BTGObjectTypes.TRIANGLE_STRIPS
					)
					triangle_strips.read(self, f)
					self.triangle_strips.append(triangle_strips)
				elif object_type == BTGObjectTypes.TRIANGLE_FACES:
					triangle_faces = BTGGeometryObject(
						BTGGeometryElementTriangleFace,
						BTGObjectTypes.TRIANGLE_FACES
					)
					triangle_faces.read(self, f)
					self.triangle_faces.append(triangle_faces)
	
	def _count_objects(self, object_list):
		return len(object_list)
	
	def _write_objects(self, object_list: typing.Iterable[BTGGeometryObject], f: typing.BinaryIO):
		for obj in object_list:
			binary.write_char(f, chr(obj.object_type).encode("ascii"))
			obj.write(self, f)
	
	@dispatch
	def write(self):
		if self.path:
			self.write(self.path)
		else:
			raise RuntimeError("ReaderWriterBTG.write called without path and self.path is not set !")
	
	@dispatch
	def write(self, path: str):
		fopen = (lambda path, mode: gzip.open(path, mode, compresslevel=9)) if path.endswith(".gz") else open
		with fopen(path, "wb") as f:
			binary.write_uint(f, (ord("S") << 24) + (ord("G") << 16) + self.version)
			binary.write_uint(f, int(time.time()))
			
			num_objects = 5
			for member in (self.points, self.triangle_fans, self.triangle_strips, self.triangle_faces):
				#num_objects += self._count_objects(member)
				num_objects += len(member)
			
			if self.version == 10:
				binary.write_int(f, num_objects)
			elif self.version == 7:
				binary.write_ushort(f, num_objects)
			else:
				binary.write_short(f, num_objects)
			
			for member in (self.bs, self.vertex_list, self.color_list, self.normal_list, self.texcoord_list):
				binary.write_char(f, chr(member.object_type).encode("ascii"))
				member.write(self, f)
			
			for member in (self.points, self.triangle_faces, self.triangle_fans, self.triangle_strips):
				self._write_objects(member, f)
	

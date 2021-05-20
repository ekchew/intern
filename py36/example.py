#!/usr/bin/env python3

from intern.intern import Intern
from intern.internable import Internable

@Intern
class ColorA:
	def __init__(self, r, g, b):
		self.r = r
		self.g = g
		self.b = b
	def astuple(self):
		return (self.r, self.g, self.b)

colorA1 = ColorA(1.0, 0.0, 0.0)
colorA2 = ColorA(1.0, 0.0, 0.0)
colorA3 = ColorA(1.0, 1.0, 0.0)
print("colorA2 is colorA1?", colorA2 is colorA1)
print("colorA3 is colorA1?", colorA3 is colorA1)

class ColorB(Internable):
	def __init__(self, r, g, b):
		self.r = r
		self.g = g
		self.b = b
	def astuple(self):
		return (self.r, self.g, self.b)

colorB1 = ColorB.MakeInterned(1.0, 0.0, 0.0)
colorB2 = ColorB.MakeInterned(1.0, 0.0, 0.0)
colorB3 = ColorB(1.0, 0.0, 0.0)
print("colorB2 is colorB1?", colorB2 is colorB1)
print("colorB3 is colorB1?", colorB3 is colorB1)

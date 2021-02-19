# intern

A Python module that helps prevent duplicate allocations of identical immutable objects.

## Overview

I originally wrote this module to help with a graphics library I was working on and thought perhaps others would find it useful? The library allowed you to attach stylistic attributes to a graphic object such as its color, text font, etc. But often you wind up using the same attribute in many places, and it seemed a waste to me to allocate multiple objects containing the exact same data that never change.

The `Intern` metaclass registers objects in a global dictionary and eliminates duplicates by returning a reference to an existing object rather than a new one where possible. The dictionary stores weak references to these objects so that they should still deallocate normally when the object is no longer in use. (The dictionary entry itself also gets removed via a custom `__del__()` method applied to your class.)

## Example (Python 3)

	>>> from intern import Intern
	>>> class Color(metaclass=Intern):
	...     def __init__(self, r, g, b):
	...             self.r = r
	...             self.g = g
	...             self.b = b
	...     def __hash__(self):
	...             return hash((self.r, self.g, self.b))
	...     def __eq__(self, other):
	...             return (self.r, self.g, self.b) == (other.r, other.g, other.b)
	... 
	>>> color1 = Color(1.0, 0.0, 0.0)
	>>> color2 = Color(1.0, 0.0, 0.0)
	>>> color1 is color2
	True

Here, we have written a `Color` class and instantiated it twice with the same (red) color. Note the last query reads `color1 is color2`. `color1 == color2` would be true regardless of whether the class interns, but `color1 is color2` means both variables are references to the same single object.

Note that interning should only ever be done on an immutable class! If you started changing `color1`'s attributes after the fact, the internment logic will break down.

You could use property decorators to ensure the attributes are read-only.

	def __init__(self, r, g, b):
		self.__r = r
		# etc.
	
	@property
	def r(self): return self.__r
	# etc.

You could also offer a `MutableColor` class that doesn't intern in case anyone actually needs that.

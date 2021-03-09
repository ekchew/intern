from .intern import _details
from typing import ClassVar, Dict
import threading

class Internable:
	"""
	Internable is a base class you can use to intern instances of any class that
	inherits from it. Unlike with the intern.Intern decorator approach, the
	internment is not compulsory. Objects only get interned if you call the
	MakeInterned() class method to instantiate them.

	Example:
		>>> class Color(Internable):
		...     def __init__(self, r, g, b):
		...         self.r = r
		...         self.g = g
		...         self.b = b
		...     def __hash__(self):
		...         return hash((self.r, self.g, self.b))
		...     def __eq__(self, rhs):
		...         return (self.r, self.g, self.b) == (rhs.r, rhs.g, rhs.b)
	    ...
		>>> color1 = Color.MakeInterned(1.0, 0.0, 0.0)
		>>> color2 = Color.MakeInterned(1.0, 0.0, 0.0)
		>>> color3 = Color(1.0, 0.0, 0.0)
		>>> color2 is color1
		True
		>>> color3 is color1
		False

	Aside from this opt-in internment, Internable may be useful in some
	situations in which it is problematic to subclass your class using the
	decorator (e.g. Generic classes are notoriously difficult to subclass).

	WARNING:
		As with the @Intern decorator, MakeInterned()-allocated objects must
		never be modified! Designing an idiot-proof class is a bit trickier with
		Internable, however, in that whether an instance may be altered depends
		on whether it was interned. Here is a safer version of the Color class
		above:

			class Color(Internable):
				@property
				def r(self): return self.__rgb[0]
				@r.setter
				def r(self, v): self.__set(0, v)
				@property
				def g(self): return self.__rgb[1]
				@g.setter
				def g(self, v): self.__set(1, v)
				@property
				def b(self): return self.__rgb[2]
				@b.setter
				def b(self, v): self.__set(2, v)

				def __init__(self, r, g, b):
					self.__rgb = [r, g, b]
				def __set(self, i, v):
					assert not self.isInterned()
					self.__rgb[i] = v
	"""

	__gLock: ClassVar = threading.Lock()
	__gDict: ClassVar[_details.Dct] = {}

	@classmethod
	def MakeInterned(cls, *args, **kwargs):
		"""
		Allocates an interned class object.

		Args:
			cls (type): your class that inherits from Internable
			*args: positional args for your class's __init__() method
			**kwargs: key word args for your class's __init__() method

		Returns:
			cls: an instance of your class
				This may not be a new object if MakeInterned() was called
				earlier with the same arguments (unless the earlier object has
				already been deallocated).
		"""
		obj = cls(*args, **kwargs)
		return _details.RegisterObj(cls.__gLock, cls.__gDict, obj)

	def isInterned(self) -> bool:
		"""
		Returns:
			True if the current object was allocated by MakeInterned().
			False if it was instantiated directly.
		"""
		key = hash(self)
		with self.__gLock:
			try: val = self.__gDict[key]
			except KeyError: pass
			else:
				objID = id(self)
				if val.__class__ is cls.Info:
					return objID == val.objID
				else:
					for info in val:
						if objID == info.objID:
							return True
		return False
	def __del__(self):
		"""
		This custom __del__() method unregisters any interned object from the
		internal dict global once the last reference to it expires.
		"""
		_details.UnregisterObj(self.__gLock, self.__gDict, self)

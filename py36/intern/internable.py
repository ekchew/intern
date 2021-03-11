from .intern import _details
from typing import ClassVar, Dict
import threading

class Internable:
	"""
	Internable is a base class you can use to intern instances of any class that
	inherits from it. Unlike with the intern.Intern decorator approach, the
	internment is not compulsory. Objects only get interned if you call the
	MakeInterned() class method to instantiate them.
	"""

	class Immutable(Exception): pass

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
		tup = _details.AsTuple(self)
		key = _details.HashObj(self, tup)
		with self.__gLock:
			try: val = self.__gDict[key]
			except KeyError: pass
			else:
				objID = id(self)
				if val.__class__ is _details.Info:
					return objID == val.objID
				else:
					for info in val:
						if objID == info.objID:
							return True
		return False
	def assertMutable(self):
		"""
		It is a good idea to call this from any setter methods.

		Raises:
			Internable.Immutable if current object is interned
		"""
		if self.isInterned():
			raise self.Immutable("interned objects cannot be modified")
	def __del__(self):
		"""
		This custom __del__() method unregisters any interned object from the
		internal dict global once the last reference to it expires.
		"""
		_details.UnregisterObj(self.__gLock, self.__gDict, self)

from typing import Any, ClassVar, Dict, List, Union
from weakref import ref, ReferenceType
import threading

class _details:

	class Info:
		objID: int
		wkRef: ReferenceType
		def __init__(self, obj):
			self.objID = id(obj)
			self.wkRef = ref(obj)

	Key = int
	Val = Union[Info, List[Info]]
	Dct = Dict[Key, Val]

	@classmethod
	def RegisterObj(cls, lock, dct: Dct, obj: Any) -> Any:
		retObj = obj
		key = hash(obj)
		with lock:
			try: val = dct[key]
			except KeyError: dct[key] = cls.Info(obj)
			else:
				if val.__class__ is cls.Info:
					if obj == val.wkRef():
						retObj = val.wkRef()
					else:
						dct[key] = [val, cls.Info(obj)]
				else:
					for info in val:
						if obj == info.wkRef():
							retObj = info.wkRef()
							break
					else:
						val.append(cls.Info(obj))
		return retObj
	@classmethod
	def UnregisterObj(cls, lock, dct: Dct, obj: Any):
		key = hash(obj)
		with lock:
			try: val = dct[key]
			except KeyError: pass
			else:
				objID = id(obj)
				if val.__class__ is cls.Info:
					if objID == val.objID:
						del dct[key]
				else:
					for i, info in enumerate(val):
						if objID == info.objID:
							del val[i]
							if len(val) == 1:
								dct[key] = val[0]
							break

def Intern(baseCls, *args, **kwargs):
	"""
	Intern is a class decorator. If you have an immutable class, you can
	decorate it to prevent multiple allocations with the same data.

	Example:

		>>> @Intern
		... class Color:
		...     def __init__(self, r, g, b):
		...         self.r = r
		...         self.g = g
		...         self.b = b
		...     def __hash__(self):
		...         return hash((self.r, self.g, self.b))
		...     def __eq__(self, rhs):
		...         return (self.r, self.g, self.b) == (rhs.r, rhs.g, rhs.b)
	    ...
		>>> color1 = Color(1.0, 0.0, 0.0)
		>>> color2 = Color(1.0, 0.0, 0.0)
		>>> color2 is color1
		True

	Without the @Intern, color1 and color2 would be different objects. While
	color2 == color1 would be True in either case, color2 is color1 would be
	False. Only with interning would you get the same object back twice.

	Implementation Notes:
		- Objects get interned into an internal thread-safe global dict, and as
		  such, need to be both hashable and equality-comparable.
		- When you allocate the Color object above, what is returned as
		  color1/color2 is technically a subclass of Color. The subclass
		  supplies custom operators like __new__() and __del__() that take care
		  of the interning.
		- There is a hidden key word argument called INTERN_RECURSE that is
		  passed through the __init__() method of the subclass for internal
		  purposes. Do not use this name as one of your own class's args -- not
		  that you are likely to.
		- The internable.Internable class offers an alternate approach in which
		  a base class handles the interning instead. This may be advantageous
		  under certain circumstances.

	WARNING:
		Do not, under any circumstances, modify the attributes within an
		interned class (at least not the ones that get hashed/compared)! This
		will destabilize the interning algorithm. You could use properties to
		permit read-only access with something along the lines:

			@property
			def r(self): return self.__r
	"""

	class Interned(baseCls):
		__gLock: ClassVar = threading.Lock()
		__gDict: ClassVar[_details.Dct] = {}

		def __new__(cls, *args, **kwargs):
			recurse = kwargs.pop("INTERN_RECURSE", True)
			if recurse:
				kwargs["INTERN_RECURSE"] = False
				obj = cls(*args, **kwargs)
				return _details.RegisterObj(cls.__gLock, cls.__gDict, obj)
			else:
				obj = super().__new__(cls)
			return obj
		def __init__(self, *args, **kwargs):
			kwargs.pop("INTERN_RECURSE", None)
			super().__init__(*args, **kwargs)
		def __del__(self):
			_details.UnregisterObj(self.__gLock, self.__gDict, self)
			try: super().__del__()
			except AttributeError: pass

	return Interned

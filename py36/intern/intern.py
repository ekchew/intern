from typing import Any, ClassVar, Optional
from weakref import ref, ReferenceType
import threading

class _details:

	class Info:
		objID: int
		wkRef: ReferenceType
		def __init__(self, obj):
			self.objID = id(obj)
			self.wkRef = ref(obj)

	@classmethod
	def RegisterObj(cls, lock, dct: dict, obj: Any) -> Any:
		retObj = obj
		tup = cls.AsTuple(obj)
		key = cls.HashObj(obj, tup)
		with lock:
			try: val = dct[key]
			except KeyError: dct[key] = cls.Info(obj)
			else:
				if val.__class__ is cls.Info:
					if cls.EqualObjs(obj, tup, val.wkRef()):
						retObj = val.wkRef()
					else:
						dct[key] = [val, cls.Info(obj)]
				else:
					for info in val:
						if cls.EqualObjs(obj, tup, info.wkRef()):
							retObj = info.wkRef()
							break
					else:
						val.append(cls.Info(obj))
		return retObj
	@classmethod
	def UnregisterObj(cls, lock, dct: dict, obj: Any):
		tup = cls.AsTuple(obj)
		key = cls.HashObj(obj, tup)
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
	@staticmethod
	def AsTuple(obj: Any) -> Optional[tuple]:
		try: return obj.asTuple()
		except AttributeError: return None
	@staticmethod
	def HashObj(obj: Any, tup: Optional[tuple]) -> int:
		return hash(tup) if tup else hash(obj)
	@staticmethod
	def EqualObjs(obj1: Any, tup1: Optional[tuple], obj2: Any) -> bool:
		def sameElemTypes(tupA: tuple, tupB: tuple) -> bool:
			#	After checking that 2 tuples are equal by value, this function
			#	performs the additional check of making sure their elements are
			#	also of the same type. The function is recursive, in order to
			#	handle nested tuples within tuples.
			for v1, v2 in zip(tupA, tupB):
				if isinstance(v1, tuple):
					if not sameElemTypes(v1, v2):
						return False
				elif type(v1) is not type(v2):
					return False
			return True

		if tup1 is None:
			return obj1 == obj2
		else:
			try:
				tup2 = obj2.asTuple()
			except AttributeError:
				return False
			return tup1 == tup2 and sameElemTypes(tup1, tup2)

def Intern(baseCls, *args, **kwargs):
	"""
	Intern is a class decorator. If you have an immutable class, you can
	decorate it to prevent multiple allocations with the same data.
	"""

	class Interned(baseCls):
		__gLock: ClassVar = threading.Lock()
		__gDict: ClassVar[dict] = {}

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

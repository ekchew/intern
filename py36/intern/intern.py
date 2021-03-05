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

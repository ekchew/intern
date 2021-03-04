from __future__ import annotations

from typing import ClassVar, List, Union
from weakref import ref, ReferenceType
import threading

def InternCls(baseCls, *args, **kwargs):
	class Interned(baseCls):
		__DictVal = Union[ReferenceType,List[ReferenceType]]
		__gDict: ClassVar[Dict[int,__DictVal]] = {}
		__gLock: ClassVar = threading.Lock()
		def __new__(cls, *args, **kwargs):
			recurse = kwargs.pop("INTERN_RECURSE", True)
			if recurse:
				kwargs["INTERN_RECURSE"] = False
				obj = cls(*args, **kwargs)
				key = hash(obj)
				with cls.__gLock:
					try:
						val = cls.__gDict[key]
					except KeyError:
						cls.__gDict[key] = ref(obj)
					else:
						if val.__class__ is list:
							for r in val:
								if obj == r():
									return r()
							else:
								val.append(ref(obj))
						elif obj == val():
							return val()
						else:
							cls.__gDict[key] = [val, ref(obj)]
			else:
				obj = super().__new__(cls)
			return obj
		def __init__(self, *args, **kwargs):
			kwargs.pop("INTERN_RECURSE", None)
			super().__init__(*args, **kwargs)
		def __del__(self):
			with self.__gLock:
				key = hash(self)
				try:
					val = self.__gDict[key]
					if val.__class__ is list:
						for i, r in enumerate(val):
							if self == r():
								del val[i]
								break
					elif self == val():
						del self.__gDict[key]
				except KeyError: pass
	return Interned

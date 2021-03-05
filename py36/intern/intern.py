from .support import DictVal, RegisterObj, UnregisterObj
from typing import ClassVar, Dict
import threading

def Intern(baseCls, *args, **kwargs):

	class Interned(baseCls):
		__gLock: ClassVar = threading.Lock()
		__gDict: ClassVar[Dict[int, DictVal]] = {}

		def __new__(cls, *args, **kwargs):
			recurse = kwargs.pop("INTERN_RECURSE", True)
			if recurse:
				kwargs["INTERN_RECURSE"] = False
				obj = cls(*args, **kwargs)
				return RegisterObj(cls.__gLock, cls.__gDict, obj)
			else:
				obj = super().__new__(cls)
			return obj

		def __init__(self, *args, **kwargs):
			kwargs.pop("INTERN_RECURSE", None)
			super().__init__(*args, **kwargs)
		def __del__(self):
			UnregisterObj(self.__gLock, self.__gDict, self)
			try: super().__del__()
			except AttributeError: pass

	return Interned

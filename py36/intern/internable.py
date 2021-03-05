from .support import DictVal, RegisterObj, UnregisterObj
from typing import ClassVar, Dict
import threading

class Internable:
	__gLock: ClassVar = threading.Lock()
	__gDict: ClassVar[Dict[int, DictVal]] = {}

	@classmethod
	def MakeInterned(cls, *args, **kwargs):
		return RegisterObj(cls.__gLock, cls.__gDict, cls(*args, **kwargs))

	def __del__(self):
		UnregisterObj(self.__gLock, self.__gDict, self)

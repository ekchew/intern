from .intern import _details
from typing import ClassVar, Dict
import threading

class Internable:
	__gLock: ClassVar = threading.Lock()
	__gDict: ClassVar[_details.Dct] = {}
	@classmethod
	def MakeInterned(cls, *args, **kwargs):
		obj = cls(*args, **kwargs)
		return _details.RegisterObj(cls.__gLock, cls.__gDict, obj)
	def __del__(self):
		_details.UnregisterObj(self.__gLock, self.__gDict, self)

from collections.abc import ItemsView, Iterable
from typing import Any, ClassVar, Generator, Optional, Union
from weakref import ref, ReferenceType
from threading import Lock

class _details:
	@classmethod
	def KeyTuple(cls, obj: Any) -> tuple:
		def genElems(seq: Union[ItemsView,Iterable],
			typ: type) -> Generator[Any,None,None]:
			for elem in seq:
				yield cls.KeyTuple(elem)
			yield typ
		def makeTuple(seq: Union[ItemsView,Iterable], typ: type) -> tuple:
			return tuple(genElems(seq, typ))
		typ = type(obj)
		try:
			tup = obj.astuple()
		except AttributeError:
			if typ in (list, tuple):
				return makeTuple(obj, typ)
			if typ is dict:
				return makeTuple(obj.items(), tup)
			try:
				return ref(obj), typ
			except TypeError:
				return obj, typ
		else:
			return makeTuple(tup, typ)
	@classmethod
	def RegisterObj(cls, lock: Lock, dct: dict, obj: Any) -> Any:
		tup = cls.KeyTuple(obj)
		with lock:
			try:
				return dct[tup]()
			except KeyError:
				dct[tup] = ref(obj)
				return obj
	@classmethod
	def UnregisterObj(cls, lock: Lock, dct: dict, obj: Any):
		tup = cls.KeyTuple(obj)
		with lock:
			dct.pop(tup, None)

def Intern(baseCls, *args, **kwargs):
	"""
	Intern is a class decorator. If you have an immutable class, you can
	decorate it to prevent multiple allocations with the same data.
	"""

	class Interned(baseCls):
		__gLock: ClassVar = Lock()
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

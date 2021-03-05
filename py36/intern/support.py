from typing import Any, Dict, List, Union
from weakref import ref, ReferenceType
import threading

DictVal = Union[ReferenceType, List[ReferenceType]]

def RegisterObj(lock, dct: Dict[int, DictVal], obj: Any):
	key = hash(obj)
	with lock:
		try:
			val = dct[key]
		except KeyError:
			dct[key] = ref(obj)
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
				dct[key] = [val, ref(obj)]
	return obj
def UnregisterObj(lock, dct: Dict[int, DictVal], obj: Any):
	key = hash(obj)
	with lock:
		try:
			val = dct[key]
			if val.__class__ is list:
				for i, r in enumerate(val):
					if obj == val():
						del val[i]
						if len(val) == 1:
							dct[key] = val[0]
						break
			elif obj == val():
				del dct[key]
		except KeyError: pass

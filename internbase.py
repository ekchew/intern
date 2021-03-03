import threading, weakref

class _InternObj(object):
	def __init__(self, obj):
		self.objID = id(obj)
		self.wkRef = weakref.ref(obj)

class InternBase(object):
	__gInternDict = dict()
	__gInternDictLock = threading.Lock()

	def __del__(cls):
		hashVal = hash(self)
		with cls.__gInternDictLock:
			entry = cls.__gInternDict.get(hashVal, None)
			if type(entry) is list:
				for i, subEntry in enumerate(entry):
					if id(self) == subEntry.objID:
						del entry[i]
						return
			elif entry and id(self) == entry.objID:
				del cls.__gInternDict[hashVal]

def MakeInterned(cls, *args, **kwargs):
	if not isinstance(cls, InternBase):
		raise ValueError("MakeInterned cls must inherit from InternBase")
	newObj = cls(*argv, **argd)
	hashVal = hash(newObj)
	with cls.__gInternDictLock:
		entry = cls.__gInternDict.get(hashVal, None)
		if entry:
			if type(entry) is list:
				for subEntry in entry:
					if newObj == subEntry.wkRef():
						return subEntry.wkRef()
				entry.append(_InternObj(newObj))
			elif newObj == entry.wkRef():
				return entry.wkRef()
			else:
				cls.__gInternDict[hashVal] = [entry, _InternObj(newObj)]
		else:
			cls.__gInternDict[hashVal] = _InternObj(newObj)
	return newObj

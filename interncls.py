def InternCls(baseCls, *args, **kwargs):
	class Subcls(baseCls):
		def __new__(cls, *args, **kwargs):
			return super().__new__(cls)
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
	return Subcls

@InternCls
class Foo:
	def __init__(self, i):
		self.i = i
	def __repr__(self):
		return f"{type(self).__name__}(i = {self.i})"
	def __hash__(self):
		return hash(self.i)
	def __eq__(self, rhs):
		return self.i == rhs.i

print(Foo(42))


"""
def Barify(baseCls, *args, **kwargs):
	class Bar(baseCls):
		def __new__(cls, *args, **kwargs):
			return super(Bar, cls).__new__(cls)
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
	return Bar

@Barify
class Foo:
	def __init__(self, i):
		self.i = i
	def __repr__(self):
		return f"{type(self).__name__}(i = {self.i})"

print(Foo(42))
"""
"""
import threading, weakref

def InternCls(baseCls, *args, **kwargs):
	class InternObj(object):
		def __init__(self, obj):
			self.objID = id(obj)
			self.wkRef = weakref.ref(obj)
	class Subcls(baseCls):
		__gInternDict = {}
		__gInternDictLock = threading.Lock()
		def __new__(cls, *args, **kwargs):
			obj = super(Subcls, cls).__new__(cls)
			hsh = hash(obj)
			with cls.__gInternDictLock:
				try:
					entry = cls.__gInternDict[hsh]
				except KeyError:
					print("interning", obj)
					cls.__gInternDict[hsh] = InternObj(obj)
				else:
					if entry.__class__ is list:
						for subentry in entry:
							if obj == subentry.wkRef():
								obj = subentry.wkRef()
								print("returning interned", obj)
								break
						else:
							entry.append(InternObj(obj))
					elif obj == entry.wkRef():
						obj = entry.wkRef()
						print("returning interned", obj)
					else:
						cls.__gInternDict[hsh] = [entry, InternObj(obj)]
						print("interning", obj)
			return obj
		def __init__(self, *args, **kwargs):
			super(Subcls, self).__init__(*args, **kwargs)
		def __del__(self):
			print("deleting", repr(self))
			hsh = hash(self)
			with self.__gInternDictLock:
				try:
					entry = cls.__gInternDict[hsh]
				except KeyError: pass
				else:
					if entry.__class__ is list:
						for i, subentry in enumerate(entry):
							if id(self) == subentry.objID:
								del entry[i]
								break
					elif id(self) == entry.objID:
						del self.__gInternDict[hsh]
	return Subcls

@InternCls
class Foo:
	def __init__(self, i):
		self.i = i
	def __repr__(self):
		return f"Foo(i = {self.i})"
	def __hash__(self):
		return hash(self.i)
	def __eq__(self, rhs):
		return self.i == rhs.i

foo1 = Foo(42)
#foo2 = Foo(42)
#foo3 = Foo(42)
print("foo1.i:", foo1.i)
"""

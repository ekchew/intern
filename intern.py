"""
This module implements a metaclass called Intern, which is designed to eliminate
duplicate allocations of identical immutable objects.

If you try to create a new object with the same arguments as a previous one, you
will get a reference to the previous object rather than a newly allocated
object.

Usage:
	The syntax for using a metaclass unfortunately depends on
	which version of Python you are running.

		Python 2:
			class Foo(object):
				__metaclass__=Intern

		Python 3:
			class Foo(metaclass=Intern):

	You can alternatively use the with_metaclass() function available in certain
	modules to smooth over this incompatibility.

	Your class also needs to implement __eq__() and __hash__() methods so that
	instances can be installed into a global dictionary maintained internally by
	Intern.

	(Note that Intern overloads the __del__() method to do some housekeeping. If
	you disable this by overloading it yourself, however, it's not the end of
	the world. It will leave some dangling object references kicking around, but
	they're only weak references, so your objects should deallocate normally
	regardless.)
"""

import threading, weakref

class _InternObj(object):
	"""
	Intern creates a record of type _InternObj for each object it is tracking.
	For internal use.

	Attributes:
		objID (id):
			Needed to identify object even after the weak reference has died.
		wkRef (weakref.ref() object):
			Intern stores weak rather than regular references to objects so that
			they can be properly deallocated once they are no longer in use.
	"""
	def __init__(self, obj):
		self.objID = id(obj)
		self.wkRef = weakref.ref(obj)

class Intern(type):
	"""
	Attributes:
		__gInternDict (dict):
			This global dictionary stores an _InternObj for every object the
			module user instantiates. The keys are integer hashes derived from
			the object. The corresponding value is typically an _InternObj, but
			in the unlikely event of a hash value collision, it may be a list of
			_InternObj instead.
		__gInternDictLock (threading.Lock() object):
			This mutex prevents simultaneous access to the __gInternDict global
			in a multithreaded environment.
	"""
	def __init__(cls, *argv):
		"""
		Besides setting up the aforementioned class attributes, this method
		replaces the instantiated class's __del__() method.
		"""
		super(Intern, cls).__init__(*argv)
		cls.__gInternDict = {}
		cls.__gInternDictLock = threading.Lock()

		def delFn(self):
			"""
			The __del__() method gets called once an object's internal reference
			count drops to zero. At this point, the weak reference contained
			within __gInternDict dies, but we should still remove its entry from
			the dictionary. This alternate __del__() implementation does so.
			"""

			#	Look for the current object's hash value within __gInternDict.
			hashVal = hash(self)
			with cls.__gInternDictLock:
				entry = cls.__gInternDict.get(hashVal, None)

				#	In the case that the dictionary entry is a list of
				#	_InternObj, we need to iterate through the list and delete
				#	the one matching self. (Yes, this is an O(N) operation, but
				#	one would never expect N to be large unless the hash
				#	function really sucks.)
				if type(entry) is list:
					for i, subEntry in enumerate(entry):

						#	Note that by the time __del__ is called, the weak
						#	reference is likely dead, so testing self ==
						#	subEntry.wkRef() may not work since the right-hand
						#	side might already be None. But since we have
						#	recorded the object ID as well, we can use that to
						#	look for a match instead.
						if id(self) == subEntry.objID:
							del entry[i]
							return

				#	In the much more likely case that there is only one object
				#	with a particular hash value, we can simply remove its
				#	entry from the dictionary. (You might think that self would
				#	have to exist somewhere in the dictionary so testing that
				#	entry is not None should not be necessary. That would be
				#	true for any instance created by the module user, but the
				#	__call__() method below creates an instance internally
				#	which may never make it into the dictionary.)
				elif entry and id(self) == entry.objID:
					del cls.__gInternDict[hashVal]

		#	Install the alternate __del__() function in the class.
		setattr(cls, "__del__", delFn)

	def __call__(cls, *argv, **argd):
		"""
		This method intercepts when the module user attempts to create a class
		object. It looks up whether an identical object has already been created
		and will return that instead. Otherwise, it will allocate the new
		object, register it into the dictionary, and return it.
		"""
		return cls.Instance(*argv, **argd)[0]

	def Instance(cls, *argv, **argd):
		"""
		If you had a class Foo that uses the Intern metaclass, calling
		Foo.Instance(arg) would be equivalent to calling Foo(arg) except that
		the former returns a tuple containing the object reference and a boolean
		indicating whether or not the object had to be allocated.

		Args:
			argv (list):
				Positional arguments to pass into your class's __init__()
				method.
			argd (dict):
				Key word arguments to pass into your class's __init__()
				method.

		Returns:
			tuple (cls, bool):
				The first argument of the tuple is the object itself. The second
				argument will True if a new instance had to be allocated or
				False if an existing instance was available.
		"""

		#	Allocate a new object using the input arguments. This instance may
		#	eventually be discarded if it is not needed.
		newObj = type.__call__(cls, *argv, **argd)

		#	Check if the object's hash value is already registered.
		hashVal = hash(newObj)
		with cls.__gInternDictLock:
			entry = cls.__gInternDict.get(hashVal, None)

			#	If it is registered, the corresponding entry could be a list or
			#	an _InternObj record.
			if entry:

				#	In the case that it is a list, we need to walk through it
				#	in search of a member containing the same data as our new
				#	object.
				if type(entry) is list:
					for subEntry in entry:

						#	If a data match is found, return a reference to it
						#	and let newObj die.
						if newObj == subEntry.wkRef():
							return subEntry.wkRef(), False

					#	If nothing matches the new object, add it to the list
					#	as a new _InternObj.
					entry.append(_InternObj(newObj))

				#	In this case, the entry itself should be an _InternObj.
				#	Check if its weak-referenced object matches our new object
				#	in terms of their contents.
				elif newObj == entry.wkRef():
					return entry.wkRef(), False

				#	Otherwise replace the entry with a list containing both the
				#	old object and new one.
				else:
					cls.__gInternDict[hashVal] = [entry, _InternObj(newObj)]

			#	With no entry for the calculated hash value, we should create a
			#	new one.
			else:
				cls.__gInternDict[hashVal] = _InternObj(newObj)

		#	Finding ourselves here means we were unable to substitute an
		#	existing object for the new one.
		return newObj, True

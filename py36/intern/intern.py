from collections.abc import ItemsView, Iterable, Iterator
from typing import Any, ClassVar, Union
from threading import Lock
from weakref import ref


class _details:
    # A class used as a namespace to hide implementation details.

    @classmethod
    def KeyTuple(cls, obj: Any, recursing: bool = False) -> tuple:
        # Given an object, returns a tuple representing its data that can
        # (hopefully!) be hashed and equality-compared for the sake of using
        # it as a dict key.
        #
        # Args:
        #     obj: an object
        #     recursing: is this a recursive call to KeyTuple()?
        # Returns: a tuple representing obj data

        def genElems(
            ctnr: Union[ItemsView, Iterable], typ: type
        ) -> Iterator[Any]:
            # Given some sort of container, genElems() calls KeyTuple
            # recursively on its elements. It also yields the object type at
            # the end. The type is important because we do not want to intern
            # 2 objects of different types, even if their data turn out to be
            # equal.
            for elem in ctnr:
                yield cls.KeyTuple(elem, recursing=True)
            yield typ

        def makeTuple(seq: Union[ItemsView, Iterable], typ: type) -> tuple:
            # makeTuple() simply returns a tuple formed out of the elements
            # yielded by genElems().
            return tuple(genElems(seq, typ))

        typ = type(obj)

        # First attempt to call obj's astuple() method.
        try:
            tup = obj.astuple()

        except AttributeError:

            # Evidently, there is no astuple() method. Next, we check to see
            # obj is a common container type. (At this point, we are only
            # dealing with the types you might encounter from a Python 3.7+
            # dataclass's astuple() method. More types may be supported in
            # the future.)
            if typ in (list, tuple):
                return makeTuple(obj, typ)

            # In the case of a dict, we convert it to a tuple of tuples
            # (plus a type element at the end), where the inner tuples are
            # key-value pairs as accessed through the dict items() method.
            if typ is dict:
                return makeTuple(obj.items(), typ)

            # At this point, it looks like we are dealing with a black box obj
            # that we cannot discern any more info about. We will return it in
            # a tuple along with its data type. If it is the primary object
            # (as opposed to a subobject being handled by a recursive call to
            # KeyTuple()), this tuple should contain a weak reference to the
            # object so that it can eventually die when no longer in use
            # outside the internment dict.
            return (obj if recursing else ref(obj), typ)

        else:

            # Even if we already have obj in tuple from (from the astuple()
            # call), we want to tack on the object's data type (see note
            # under genElems() regarding this).
            return makeTuple(tup, typ)

    @classmethod
    def RegisterObj(cls, lock: Lock, dct: dict, obj: Any) -> Any:
        # Looks up whether a particular object has already been interned.
        # If so, the previously interned object is returned. Otherwise, the
        # input object is returned once it has been installed in the
        # internment dictionary.
        #
        # Args:
        #     lock: used to manage access to dct (which should be a global)
        #     dct: the internment dictionary
        #         Maps key tuples onto weak references to interned objects.
        #     obj: the object to register
        #
        # Returns: either the input obj or a previously interned equivalent

        # Get the object data in tuple form.
        tup = cls.KeyTuple(obj)

        with lock:

            # Return the interned object, if any, whose key matches the tuple.
            try:
                return dct[tup]()

            # If the object has yet to be interned, we intern it by adding a
            # new item to the dictionary. The tuple serves as the key and a
            # weak reference to the object serves as the value. (Weak
            # references are appropriate because we do not want the object
            # to live on after all references outside the internment dict
            # have expired. In fact, we want the object's __del__() method
            # to remove it from the dict at that point.)
            except KeyError:
                dct[tup] = ref(obj)
                return obj

    @classmethod
    def UnregisterObj(cls, lock: Lock, dct: dict, obj: Any):
        # This method should get called by the __del__() methods of objects
        # interned in a given dictionary. It removes the dict entry
        # corresponding to the object.
        #
        # Args:
        #     lock: used to manage access to dct (which should be a global)
        #     dct: the internment dictionary
        #     obj: the object to remove from dct
        tup = cls.KeyTuple(obj)
        with lock:

            # With Internable objects, it's optional to intern but __del__()
            # will still try to unregister them. So we can't assume the object
            # will always be there -- hence, the non-exception-throwing pop()
            # call here.
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
            try:
                super().__del__()
            except AttributeError:
                pass

    return Interned

from .intern import _details
from typing import ClassVar
from threading import Lock


class Internable:
    """
    Internable is a base class you can use to intern instances of any class
    that inherits from it. Unlike with the intern.Intern decorator approach,
    the internment is not compulsory. Objects only get interned if you call the
    MakeInterned() class method to instantiate them.
    """

    class Immutable(Exception):
        pass

    __gLock: ClassVar[Lock] = Lock()
    __gDict: ClassVar[dict] = {}

    @classmethod
    def MakeInterned(cls, *args, **kwargs):
        """
        Allocates an interned class object.

        Args:
            cls (type): your class that inherits from Internable
            *args: positional args for your class's __init__() method
            **kwargs: key word args for your class's __init__() method

        Returns:
            cls: an instance of your class
                This may not be a new object if MakeInterned() was called
                earlier with the same arguments (unless the earlier object has
                already been deallocated).
        """
        obj = cls(*args, **kwargs)
        return _details.RegisterObj(cls.__gLock, cls.__gDict, obj)

    @classmethod
    def MakeInternable(cls, *args, **kwargs):
        """
        While MakeInterned() always interns the class object, MakeInternable()
        gives you the option of interning it or not, depending on a key word
        argument.

        Args:
            *args: positional args to pass to cls.__init__()
            intern (bool, kwarg): intern new cls instance?
                Defaults to False.
            passOn (bool, kwarg): pass intern kwarg on to cls.__init__()
                You might set this True if your class includes Internable
                subobjects that you may want to intern as well? Defaults to
                False.
            *kwargs: remaining key word args get passed to cls.__init__()
                The passOn arg is not itself passed on, but of course affects
                whether or not the intern arg is.

        Returns:
            cls: an instance of your class which may or may not be interned
        """
        passOn = kwargs.pop("passOn", False)
        intern = kwargs.get("intern", False) if passOn \
            else kwargs.pop("intern", False)
        return cls.MakeInterned(*args, **kwargs) if intern \
            else cls(*args, **kwargs)

    def isInterned(self) -> bool:
        """
        Returns:
            True if the current object was allocated by MakeInterned().
            False if it was instantiated directly.
        """
        tup = _details.KeyTuple(self)
        with self.__gLock:
            return tup in self.__gDict

    def assertMutable(self):
        """
        It is a good idea to call this from any setter methods.

        Raises:
            Internable.Immutable if current object is interned
        """
        if self.isInterned():
            raise self.Immutable("interned objects cannot be modified")

    def __del__(self):
        """
        This custom __del__() method unregisters any interned object from the
        internal dict global once the last reference to it expires.
        """
        _details.UnregisterObj(self.__gLock, self.__gDict, self)

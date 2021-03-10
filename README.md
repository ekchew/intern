# intern

Two Python modules and a C++ header that help eliminate duplicate allocations of
identical, immutable objects.

## Requirements

* Python 3.6 or later
* C++17 or later

To be clear, there are no code dependencies between the Python and C++. They are self-contained implementations for each language, so you can pick whichever one you want and discard the other.

There are also no external dependencies beyond the standard library in either case.

## Overview

The first time you ask for an interned object, it is dynamically allocated. But
before you receive a reference to it, it is registered into a global, internal
look-up table.

Later, if you ask for another identical object, you may receive a secondary
reference to the registered object rather than a freshly allocated one.

The obvious reason to intern objects is to save memory by preventing redundant
object allocations. In some cases, it may also be useful to check if two
references point to the same object.

For example, in many graphics libraries, it is costly to change attributes like
color, texture, text font, etc. as you render graphic elements. If you had two
consecutive elements in your render pipeline that share identical attributes,
there should be no need to set the attributes again for the second element.
Once the attributes are interned, you can quickly tell which are identical.

**WARNING: once you have interned an object, you must never modify it!**

The internment logic will break down if an object is modified. Internment
implies immutability.

A few implementation notes:

* Python's internal look-up table is a dict. C++'s is a std::unordered_map. In
either case, your class may need to be both hashable and equality-comparable.
The alternative is to have it export a tuple representation of the object data
that can be both hashed and compared. More on that later.
* In both the Python and C++ implementations, the look-up table is guarded by a
mutex to keep it thread-safe.
* Once the final reference to an object expires, the object is removed from the
look-up table. (In C++, this occurs immediately. In Python, it is subject to the
garbage collection logic.) This implies that an identical object may, in some
circumstances, need to be allocated a second time if the previous reference(s)
were allowed to expire.

## Python

The Python implementation includes two modules: **intern.py** and
**internable.py**. They take different approaches to interning objects.

In intern.py is a class decorator called Intern. Applying this decorator to your
class causes instances to get interned as you normally go about instantiating
them.

### Example: @Intern decorator

	>>> @Intern
	... class Color
	...     def __init__(self, r, g, b):
	...         self.r = r
	...         self.g = g
	...         self.b = b
	...     def asTuple(self):
	...         return (self.r, self.g, self.b)
	...
	>>> color1 = Color(1.0, 0.0, 0.0)
	>>> color2 = Color(1.0, 0.0, 0.0)
	>>> color2 is color1
	True

Without the `@Intern` decorator, `color2 is color1` would report `False`. Both
objects may store the same red color, but they would not be the same object.
They would be two separately allocated objects.

`asTuple` is a special method the interning logic looks for. If present, the
returned `tuple` representation of your object data is used internally for
hashing and comparison purposes. In you do not provide this method in your
class, you must provide the `__hash__` and `__eq__` operators instead.

--------------------------------------------------------------------------------

An alternative to using the decorator is to inherit from the `Internable` base
class. (The decorator subclasses your class to implement custom operators like
`__new__` and `__del__`. `Internable` puts these in the base class, so in a
sense, it takes the opposite approach to `@Intern`.)

With `Internable`, you have a choice to intern or not intern specific instances
of your class. To intern them, call the `MakeInterned` class method defined in
`Internable`. To *not* intern them, instantiate you class as you normally would.

### Example: Internable base class

	>>> class Color(Internable)
	...     def __init__(self, r, g, b):
	...         self.r = r
	...         self.g = g
	...         self.b = b
	...     def asTuple(self):
	...         return (self.r, self.g, self.b)
	...
	>>> color1 = Color.MakeInterned(1.0, 0.0, 0.0)
	>>> color2 = Color.MakeInterned(1.0, 0.0, 0.0)
	>>> color3 = Color(1.0, 0.0, 0.0)
	>>> color2 is color1
	True
	>>> color3 is color1
	False

Here, `color3` is a different object from `color1`/`color2`, since it was not
created by `MakeInterned`.

## C++

The C++ approach looks somewhat similar to the `Internable` class approach
except there is no actual base class you need to inherit from. It is all handled
through template logic instead.

You call the `MakeInterned` factory function to instantiate interned objects
which are returned as `std::shared_ptr<T>`, where `T` is your class.

### Example: C++

Source:

	#include "intern.hpp"
	#include <array>
	#include <iostream>

	struct Color {
	    using Array = std::array<float,3>;
	    float r, g, b;
	    explicit operator Array() const { return Array{r,g,b}; }
	};

	int main() {
	    using namespace intern;
	    auto pColor1 = MakeInterned<Color,Color::Array>(1.0f, 0.0f, 0.0f);
	    auto pColor2 = MakeInterned<Color,Color::Array>(1.0f, 0.0f, 0.0f);
	    std::cout << "color1 is color2: " << std::boolalpha
	        << (pColor1 == pColor2) << '\n';
	}

Output:

	color1 is color2: true

Of particular note here is this business with `Array`. It is essentially the C++
counterpart to the Python implementation's `asTuple` method. The 2nd template
argument of `MakeInterned` is optional, but if you provide it, it tells
`MakeInterned` that it can cast your class to that type.

The type needs to be a tuple-like type such as `std::array`, `std::pair`, or of
course `std::tuple` itself. Such types can be hashed and equality-compared.
(Hashing tuples is not actually supported by the standard library directly, but
`intern.hpp` implements this through its `HashTuple` utility function.)

If you omit the 2nd template argument, you will need to implement both `operator
==` and a `std::hash` specialization for your class.

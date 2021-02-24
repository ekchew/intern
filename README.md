# intern

A Python module and a C++17 header that help prevent duplicate allocations of
identical immutable objects.

## Overview

I originally wrote this module to help with a graphics library I was working on
and thought perhaps others would find it useful? The library allowed you to
attach stylistic attributes to a graphic object such as its color, text font,
etc. But often you wind up using the same attribute in many places, and it
seemed a waste to me to allocate multiple objects containing the exact same data
that never change.

In the Python implementation, the `Intern` metaclass registers objects in a
global dictionary and eliminates duplicates by returning a reference to an
existing object rather than a new one where possible. The dictionary stores weak
references to these objects so that they should still deallocate normally when
the object is no longer in use. (The dictionary entry itself also gets removed
via a custom `__del__()` method applied to your class.)

The C++ implementation allocates shared pointers from a global internal
unordered map that is more or less equivalent to Python's global dictionary.

## Example (Python 3)

	>>> from intern import Intern
	>>> class Color(metaclass=Intern):
	...     def __init__(self, r, g, b):
	...             self.r = r
	...             self.g = g
	...             self.b = b
	...     def __hash__(self):
	...             return hash((self.r, self.g, self.b))
	...     def __eq__(self, other):
	...             return (self.r, self.g, self.b) == (other.r, other.g, other.b)
	... 
	>>> color1 = Color(1.0, 0.0, 0.0)
	>>> color2 = Color(1.0, 0.0, 0.0)
	>>> color1 is color2
	True

Here, we have written a `Color` class and instantiated it twice with the same
(red) color. Note the last query reads `color1 is color2`. `color1 == color2`
would be true regardless of whether the class interns, but `color1 is color2`
means both variables are referencing the same single object.

Note that interning should only ever be done on an immutable class! If you
started changing `color1`'s attributes after the fact, the internment logic
would break down.

You could use property decorators to ensure the attributes are read-only.

	def __init__(self, r, g, b):
		self.__r = r
		# etc.
	
	@property
	def r(self): return self.__r
	# etc.

You could also offer a `MutableColor` class that doesn't intern in case anyone actually needs that.

## Examples (C++17)

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

This is more or less the same as the Python example. Note this business with the Array type. It saves you the trouble of having to implement `operator ==` and a `std::hash` specialization for your Color class. If you can return a simple array or tuple representation of your class data, MakeInterned can hash/compare new instances of your class with what it's already got.

Another option to get an array representation of Color would be to simply inherit Color from the array.

	#include "intern.hpp"
	#include <array>
	#include <iostream>

	using ColorArray = std::array<float,3>;
	struct Color: ColorArray {
		constexpr auto r() const noexcept { return (*this)[0]; }
		constexpr auto g() const noexcept { return (*this)[1]; }
		constexpr auto b() const noexcept { return (*this)[2]; }
	};

	int main() {
		using namespace intern;
		auto pColor1 = MakeInterned<Color,ColorArray>(1.0f, 0.0f, 0.0f);
		auto pColor2 = MakeInterned<Color,ColorArray>(1.0f, 0.0f, 0.0f);
		std::cout << "color1 is color2: " << std::boolalpha
			<< (pColor1 == pColor2) << '\n';
	}

The output would be the same. The second implementation would be somewhat faster
and would let you write things like `pColor1->at(0)` for the red color and so
on. Whether you want to allow that is your call.

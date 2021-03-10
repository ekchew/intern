from intern.intern import Intern
from intern.internable import Internable

@Intern
class Foo:
	def __init__(self, x):
		self.x = x
	def asTuple(self):
		return (self.x,)

foo1 = Foo(42)
foo2 = Foo(42)
print(foo1 is foo2)

class Bar(Internable):
	def __init__(self, x):
		self.x = x
	def asTuple(self):
		return (self.x,)

bar1 = Bar.MakeInterned(42)
bar2 = Bar.MakeInterned(42)
print(bar1 is bar2)

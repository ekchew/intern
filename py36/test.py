from intern.intern import Intern

@Intern
class Foo:
	def __init__(self, x):
		self.x = x
	def __hash__(self):
		return hash(self.x)
	def __eq__(self, rhs):
		return self.x == rhs.x

foo1 = Foo(42)
foo2 = Foo(42)
print(foo1 is foo2)

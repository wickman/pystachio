from twitter.pystachio import *

class Resources(Composite):
  cpu = Required(Float)
  ram = Integer
  disk = Integer

class Process(Composite):
  name = Required(String)
  resources = Map(String, Resources)

def test_composite_interpolation():
  p = Process(name = "hello")
  assert p(resources = {'foo': Resources()}) == \
         p(resources = {'{{whee}}': Resources()}).bind(whee='foo')
  assert p(resources = {'{{whee}}': Resources(cpu='{{whee}}')}).bind(whee=1.0) == \
         p(resources = {'1.0': Resources(cpu=1.0)})

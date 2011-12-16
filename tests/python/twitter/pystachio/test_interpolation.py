from twitter.pystachio import *

def test_composite_interpolation():
  class Resources(Composite):
    cpu = Required(Float)
    ram = Integer
    disk = Integer

  class Process(Composite):
    name = Required(String)
    resources = Map(String, Resources)

  assert Process(name = "hello", resources = {'foo': Resources()}) == \
         Process(name = "hello", resources = {'{{whee}}': Resources()}).bind(whee='foo')
  
from pystachio.basic import *
from pystachio.composite import *
from pystachio.container import Map

# TODO(wickman)  Do more .find(...) stress testing.

def test_basic_types():
  class Resources(Struct):
    cpu = Float
    ram = Integer
  assert Resources().check().ok()
  assert Resources(cpu = 1.0).check().ok()
  assert Resources(cpu = 1.0, ram = 100).check().ok()
  assert Resources(cpu = 1, ram = 100).check().ok()
  assert Resources(cpu = '1.0', ram = 100).check().ok()


def test_nested_composites():
  class Resources(Struct):
    cpu = Float
    ram = Integer
  class Process(Struct):
    name = String
    resources = Resources
  assert Process().check().ok()
  assert Process(name = "hello_world").check().ok()
  assert Process(resources = Resources()).check().ok()
  assert Process(resources = Resources(cpu = 1.0)).check().ok()
  assert Process(resources = Resources(cpu = 1)).check().ok()
  assert Process(name = 15)(resources = Resources(cpu = 1.0)).check().ok()


def test_defaults():
  class Resources(Struct):
    cpu = Default(Float, 1.0)
    ram = Integer
  assert Resources() == Resources(cpu = 1.0)
  assert Resources(cpu = 2.0)._schema_data['cpu'] == Float(2.0)

  class Process(Struct):
    name = String
    resources = Default(Resources, Resources(ram = 10))

  assert Process().check().ok()
  assert Process() == Process(resources = Resources(cpu = 1.0, ram = 10))
  assert Process() != Process(resources = Resources())
  assert Process()(resources = Empty).check().ok()


def test_composite_interpolation():
  class Resources(Struct):
    cpu = Required(Float)
    ram = Integer
    disk = Integer

  class Process(Struct):
    name = Required(String)
    resources = Map(String, Resources)

  p = Process(name = "hello")
  assert p(resources = {'foo': Resources()}) == \
         p(resources = {'{{whee}}': Resources()}).bind(whee='foo')
  assert p(resources = {'{{whee}}': Resources(cpu='{{whee}}')}).bind(whee=1.0) == \
         p(resources = {'1.0': Resources(cpu=1.0)})

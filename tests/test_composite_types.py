import pytest
from pystachio.basic import *
from pystachio.composite import *
from pystachio.container import Map, List
from pystachio.naming import Ref

# TODO(wickman)  Do more .find(...) stress testing.

def ref(address):
  return Ref.from_address(address)


def test_basic_types():
  class Resources(Struct):
    cpu = Float
    ram = Integer
  assert Resources().check().ok()
  assert Resources(cpu = 1.0).check().ok()
  assert Resources(cpu = 1.0, ram = 100).check().ok()
  assert Resources(cpu = 1, ram = 100).check().ok()
  assert Resources(cpu = '1.0', ram = 100).check().ok()


def test_bad_inputs():
  class Resources(Struct):
    cpu = Float
    ram = Required(Integer)
  with pytest.raises(AttributeError):
    Resources(herp = "derp")
  with pytest.raises(AttributeError):
    Resources({'foo': 'bar'})
  with pytest.raises(ValueError):
    Resources(None)

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


def test_find():
  class Resources(Struct):
    cpu = Required(Float)
    ram = Integer
    disks = List(String)

  class Process(Struct):
    name = Required(String)
    resources = Map(String, Resources)

  res0 = Resources(cpu = 0.0, ram = 0)
  res1 = Resources(cpu = 1.0, ram = 1, disks = ['hda3'])
  res2 = Resources(cpu = 2.0, ram = 2, disks = ['hda3', 'hdb3'])
  proc = Process(name = "hello", resources = {
    'res0': res0,
    'res1': res1,
    'res2': res2
  })

  with pytest.raises(Namable.NotFound):
    proc.find(ref('herp'))

  assert proc.find(ref('name')) == String('hello')
  assert proc.find(ref('resources[res0].cpu')) == Float(0.0)
  assert proc.find(ref('resources[res0].ram')) == Integer(0)
  with pytest.raises(Namable.NotFound):
    proc.find(ref('resources[res0].disks'))
  with pytest.raises(Namable.NamingError):
    proc.find(ref('resources.res0.disks'))
  with pytest.raises(Namable.NamingError):
    proc.find(ref('resources[res0][disks]'))
  with pytest.raises(Namable.Unnamable):
    proc.find(ref('name.herp'))
  with pytest.raises(Namable.Unnamable):
    proc.find(ref('name[herp]'))
  assert proc.find(ref('resources[res1].ram')) == Integer(1)
  assert proc.find(ref('resources[res1].disks[0]')) == String('hda3')
  assert proc.find(ref('resources[res2].disks[0]')) == String('hda3')
  assert proc.find(ref('resources[res2].disks[1]')) == String('hdb3')

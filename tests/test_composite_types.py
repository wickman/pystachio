import pytest

from pystachio.basic import *
from pystachio.composite import *
from pystachio.container import List, Map
from pystachio.naming import Ref


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
  repr(Process(name = 15)(resources = Resources(cpu = 1.0)))
  repr(Process.TYPEMAP)


def test_typesig():
  class Process1(Struct):
    name = String
  class Process2(Struct):
    name = Required(String)
  class Process3(Struct):
    name = Default(String, "foo")
  class Process4(Struct):
    name = String
  assert Process1.TYPEMAP['name'] == Process4.TYPEMAP['name']
  assert Process1.TYPEMAP['name'] != Process2.TYPEMAP['name']
  assert Process1.TYPEMAP['name'] != Process3.TYPEMAP['name']
  assert Process2.TYPEMAP['name'] != Process3.TYPEMAP['name']
  repr(Process1.TYPEMAP['name'])


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


def test_internal_interpolate():
  class Process(Struct):
    name = Required(String)
    cmdline = Required(String)

  class Task(Struct):
    name = Default(String, 'task-{{processes[0].name}}')
    processes = Required(List(Process))

  class Job(Struct):
    name = Default(String, '{{task.name}}')
    task = Required(Task)

  assert Task().name() == String('task-{{processes[0].name}}')
  assert Task(processes=[Process(name='hello_world', cmdline='echo hello_world')]).name() == \
    String('task-hello_world')
  assert Task(processes=[Process(name='hello_world', cmdline='echo hello_world'),
                         Process(name='hello_world2', cmdline='echo hello world')]).name() == \
    String('task-hello_world')
  assert Job(task=Task(processes=[Process(name="hello_world")])).name() == \
    String('task-hello_world')


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


def test_getattr_functions():
  class Resources(Struct):
    cpu = Required(Float)
    ram = Integer
    disk = Integer

  class Process(Struct):
    name = Required(String)
    resources = Map(String, Resources)

  # Basic getattr + hasattr
  assert Process(name = "hello").name() == String('hello')
  assert Process().has_name() is False
  assert Process(name = "hello").has_name() is True


  p = Process(name = "hello")
  p1 = p(resources = {'foo': Resources()})
  p2 = p(resources = {'{{whee}}': Resources()}).bind(whee='foo')

  assert p1.has_resources()
  assert p2.has_resources()
  assert String('foo') in p1.resources()
  assert String('foo') in p2.resources()


def test_getattr_bad_cases():
  # Technically speaking if we had
  # class Tricky(Struct):
  #    stuff = Integer
  #    has_stuff = Integer
  # would be ~= undefined.

  class Tricky(Struct):
    has_stuff = Integer
  t = Tricky()
  assert t.has_has_stuff() is False
  assert t.has_stuff() is Empty

  with pytest.raises(AttributeError):
    t.this_should_properly_raise


def test_self_super():
  class Child(Struct):
    value = Integer

  class Parent(Struct):
    child = Child
    value = Integer

  class Grandparent(Struct):
    parent = Parent
    value = Integer

  parent = Parent(child=Child(value='{{super.value}}'), value=23)
  parent, _ = parent.interpolate()
  assert parent.child().value().get() == 23

  grandparent = Grandparent(parent=Parent(child=Child(value='{{super.super.value}}')), value=23)
  grandparent, _ = grandparent.interpolate()
  assert grandparent.parent().child().value().get() == 23

  parent = Parent(child=Child(value=23), value='{{child.value}}')
  parent, _ = parent.interpolate()
  assert parent.child().value().get() == 23

  parent = Parent(child=Child(value=23), value='{{self.child.value}}')
  parent, _ = parent.interpolate()
  assert parent.child().value().get() == 23

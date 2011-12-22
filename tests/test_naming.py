from copy import deepcopy
import pytest

from pystachio.base import Environment
from pystachio.naming import Ref, Namable

from pystachio.basic import *
from pystachio.container import *
from pystachio.composite import *

def ref(address):
  return Ref.from_address(address)

def test_ref_parsing():
  for input in ['', None, type, 1, 3.0, 'hork bork']:
    with pytest.raises(Ref.InvalidRefError):
      ref(input)

  ref('a').components() == [Ref.Dereference('a')]
  ref('.a').components() == [Ref.Dereference('a')]
  ref('a.b').components() == [Ref.Dereference('a'), Ref.Dereference('b')]
  ref('[a]').components() == [Ref.Index('a')]
  ref('[0].a').components() == [Ref.Index('0'), Ref.Dereference('a')]
  ref('[0][a]').components() == [Ref.Index('0'), Ref.Index('a')]
  for refstr in ['[a]b', '[]', '[[a]', 'b[[[', 'a.1', '1.a', '.[a]', '0']:
    with pytest.raises(Ref.InvalidRefError):
      ref(refstr)


def test_ref_lookup():
  oe = Environment(a = 1)
  assert oe.find(ref("a")) == '1'

  oe = Environment(a = {'b': 1})
  assert oe.find(ref("a.b")) == '1'

  oe = Environment(a = {'b': {'c': 1}, 'c': Environment(d = 2)})
  assert oe.find(ref('a.b.c')) == '1'
  assert oe.find(ref('a.c.d')) == '2'

  for address in ["a", "a.b", "a.c"]:
    with pytest.raises(Namable.NotFound):
      oe.find(ref(address))

  oe = List(String)(["a", "b", "c"])
  assert oe.find(ref('[0]')) == String('a')
  with pytest.raises(Namable.NotFound):
    oe.find(ref('[3]'))

  oe = List(Map(String,Integer))([{'a': 27}])
  oe.find(ref('[0][a]')) == Integer(27)
  Environment(foo = oe).find(ref('foo[0][a]')) == Integer(27)

def test_complex_lookup():
  class Employee(Struct):
    first = String
    last = String

  class Employer(Struct):
    name = String
    employees = List(Employee)

  twttr = Employer(
    name = 'Twitter',
    employees = [
         Employee(first = 'brian', last = 'wickman'),
         Employee(first = 'marius'),
         Employee(last = '{{default.last}}')
    ])


  assert Environment(twttr = twttr).find(ref('twttr.employees[1].first')) == String('marius')
  assert Map(String,Employer)({'twttr': twttr}).find(ref('[twttr].employees[1].first')) == String('marius')
  assert List(Employer)([twttr]).find(ref('[0].employees[0].last')) == String('wickman')
  assert List(Employer)([twttr]).find(ref('[0].employees[2].last')) == String('{{default.last}}')

def test_scope_lookup():
  refs = [ref('mesos.ports[health]'), ref('mesos.config'), ref('logrotate.filename'),
          ref('mesos.ports.http')]
  scoped_refs = filter(None, map(ref('mesos.ports').scoped_to, refs))
  assert scoped_refs == [ref('[health]'), ref('http')]

  refs = [ref('[a]'), ref('[a][b]'), ref('[a].b')]
  scoped_refs = filter(None, map(ref('[a]').scoped_to, refs))
  assert scoped_refs == [ref('[b]'), ref('b')]

def test_scope_override():
  class MesosConfig(Struct):
    ports = Map(String, Integer)
  config = MesosConfig(ports = {'http': 80, 'health': 8888})
  env = Environment({ref('config.ports[http]'): 5000}, config = config)
  assert env.find(ref('config.ports[http]')) == '5000'
  assert env.find(ref('config.ports[health]')) == Integer(8888)

def test_inherited_scope():
  class PhoneBookEntry(Struct):
    name = Required(String)
    number = Required(Integer)

  class PhoneBook(Struct):
    city = Required(String)
    people = List(PhoneBookEntry)

  sf = PhoneBook(city = "San Francisco").bind(areacode = 415)
  sj = PhoneBook(city = "San Jose").bind(areacode = 408)
  jenny = PhoneBookEntry(name = "Jenny", number = "{{areacode}}8675309")
  brian = PhoneBookEntry(name = "Brian", number = "{{areacode}}5551234")
  brian = brian.bind(areacode = 402)
  sfpb = sf(people = [jenny, brian])
  assert sfpb.find(ref('people[0].number')) == Integer(4158675309)
  assert sfpb.bind(areacode = 999).find(ref('people[0].number')) == Integer(9998675309)
  assert sfpb.find(ref('people[1].number')) == Integer(4025551234)
  assert sfpb.bind(areacode = 999).find(ref('people[1].number')) == Integer(4025551234)


def test_deepcopy_preserves_bindings():
  class PhoneBookEntry(Struct):
    name = Required(String)
    number = Required(Integer)
  brian = PhoneBookEntry(number = "{{areacode}}5551234")
  brian = brian.bind(areacode = 402)
  briancopy = deepcopy(brian)
  assert brian.find(ref('number')) == Integer(4025551234)
  assert briancopy.find(ref('number')) == Integer(4025551234)

import pytest

from pystachio import (
  List,
  String,
  Integer,
  Struct,
  Map)
from pystachio.naming import Ref, Namable, Indexed
from pystachio.environment import Environment

def test_ref_parsing():
  for input in ['', None, type, 1, 3.0, 'hork bork']:
    with pytest.raises(Ref.InvalidRefError):
      Ref(input)

  Ref('a').components() == [Ref.Dereferenced('a')]
  Ref('.a').components() == [Ref.Dereferenced('a')]
  Ref('a.b').components() == [Ref.Dereferenced('a'), Ref.Dereferenced('b')]
  Ref('[a]').components() == [Ref.Indexed('a')]
  Ref('[0].a').components() == [Ref.Indexed('0'), Ref.Dereferenced('a')]
  Ref('[0][a]').components() == [Ref.Indexed('0'), Ref.Indexed('a')]
  for refstr in ['[a]b', '[]', '[[a]', 'b[[[', 'a.1', '1.a', '.[a]', '0']:
    with pytest.raises(Ref.InvalidRefError):
      print Ref(refstr)

def test_ref_lookup():
  oe = Environment(a = 1)
  assert Ref("a").resolve(oe) == 1

  oe = Environment(a = {'b': 1})
  assert Ref("a.b").resolve(oe) == 1

  oe = Environment(a = {'b': {'c': 1}, 'c': Environment(d = 2)})
  assert Ref("a.b").resolve(oe) == {'c': 1}
  assert Ref("a.b.c").resolve(oe) == 1
  assert Ref("a.c").resolve(oe) == {'d': 2}
  assert Ref("a.c.d").resolve(oe) == 2

  oe = List(String)(["a", "b", "c"])
  assert Ref('[0]').resolve(oe) == String('a')
  with pytest.raises(Indexed.Unresolvable):
    Ref('[3]').resolve(oe)

  oe = List(Map(String,Integer))([{'a': 27}])
  Ref('[0][a]').resolve(oe) == Integer(27)
  Ref('foo[0][a]').resolve(Environment(foo = oe)) == Integer(27)

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

  assert Ref('twttr.employees[1].first').resolve(Environment(twttr = twttr)) == String('marius')
  assert Ref('[twttr].employees[1].first').resolve(
    Map(String,Employer)({'twttr': twttr})) == String('marius')
  assert Ref('[0].employees[0].last').resolve(List(Employer)([twttr])) == String('wickman')
  assert Ref('[0].employees[2].last').resolve(List(Employer)([twttr])) == String('{{default.last}}')

def test_scope_lookup():
  refs = [Ref('mesos.ports[health]'), Ref('mesos.config'), Ref('logrotate.filename'),
          Ref('mesos.ports.http')]
  scoped_refs = filter(None, map(Ref('mesos.ports').scoped_to, refs))
  assert scoped_refs == [Ref.Indexed('health'), Ref.Dereferenced('http')]

  refs = [Ref('[a]'), Ref('[a][b]'), Ref('[a].b')]
  scoped_refs = filter(None, map(Ref('[a]').scoped_to, refs))
  assert scoped_refs == [Ref.Indexed('b'), Ref.Dereferenced('b')]

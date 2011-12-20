import pytest

from pystachio import *
from pystachio.naming import Ref, Namable
from pystachio.environment import Environment

def test_ref_parsing():
  Ref('a').components() == [Ref.Dereferenced('a')]
  Ref('.a').components() == [Ref.Dereferenced('a')]
  Ref('a.b').components() == [Ref.Dereferenced('a'), Ref.Dereferenced('b')]
  Ref('[a]').components() == [Ref.Indexed('a')]
  Ref('[0].a').components() == [Ref.Indexed('0'), Ref.Dereferenced('a')]
  for refstr in ['[a]b', '[]', '[[a]', 'b[[[', 'a.1', '1.a', '.[a]', '0']:
    with pytest.raises(Ref.InvalidRefError):
      print Ref(refstr)


def test_naming():
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
         Employee(first = 'marius')
    ])

  assert Ref('twttr.employees[1].first').resolve(Environment(twttr = twttr)) == String('marius')
  assert Ref('[twttr].employees[1].first').resolve(
    Map(String,Employer)({'twttr': twttr})) == String('marius')
  assert Ref('[0].employees[0].last').resolve(
    List(Employer)([twttr])) == String('wickman')



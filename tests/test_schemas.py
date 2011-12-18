import pytest

from pystachio import *
from pystachio.schema import Schema

def test_recursive_unwrapping():
  class Employee(Composite):
    name = Required(String)
    location = Default(String, "San Francisco")
    age = Integer

  class Employer(Composite):
    name = Required(String)
    employees = Default(List(Employee), [Employee(name = 'Bob')])

  new_employer = Schema.deserialize_schema(Employer.serialize_schema())

  # For various reasons, we need to compare the repr(TYPEMAP) instead of the
  # TYPEMAP, mainly because types produced by pystachio are scoped within
  # the pystachio module:
  #
  # Employer.TYPEMAP != new_employer.TYPEMAP b/c
  #   Employer.Employee = <class 'pystachio.composite.Employee'>
  #   new_employer.Employee = <class 'test_schemas.Employee'>

  assert repr(Employer.TYPEMAP) == repr(new_employer.TYPEMAP)
  assert Employer.serialize_schema() == new_employer.serialize_schema()

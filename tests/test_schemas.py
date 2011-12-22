from pystachio import *
from pystachio.schema import Schema

def test_basic_schemas():
  BASIC_TYPES = (Integer, Float, String)

  for typ in BASIC_TYPES:
    assert Schema.deserialize_schema(typ.serialize_schema()) == typ
    assert Schema.deserialize_schema(List(typ).serialize_schema()) == List(typ)

  for typ1 in BASIC_TYPES:
    for typ2 in BASIC_TYPES:
      assert Schema.deserialize_schema(Map(typ1, typ2).serialize_schema()) == Map(typ1, typ2)

def test_complex_schemas():
  BASIC_TYPES = (Integer, Float, String)
  LIST_TYPES = map(List, BASIC_TYPES)
  MAP_TYPES = []
  for typ1 in BASIC_TYPES:
    for typ2 in BASIC_TYPES:
      MAP_TYPES.append(Map(typ1,typ2))
  for mt1 in (BASIC_TYPES, LIST_TYPES, MAP_TYPES):
    for mt2 in (BASIC_TYPES, LIST_TYPES, MAP_TYPES):
      for typ1 in mt1:
        for typ2 in mt2:
          assert Schema.deserialize_schema(Map(typ1, typ2).serialize_schema()) == Map(typ1, typ2)
          assert Schema.deserialize_schema(Map(typ2, typ1).serialize_schema()) == Map(typ2, typ1)

def test_composite_schemas_are_not_lossy():
  class C1(Struct):
    required_attribute = Required(Integer)
    optional_attribute = Float
    default_attribute  = Default(String, "Hello")
    required_list      = Required(List(String))
    optional_list      = List(Integer)
    default_list       = Default(List(Float), [1.0, Float(2.0)])
    required_map       = Required(Map(String, Integer))
    optional_map       = Map(Integer, Float)
    default_map        = Default(Map(Float, Integer), {1.0: 2, 2.0: 3})

  class M1(Struct):
    required_attribute = Required(Integer)
    optional_attribute = Float
    default_attribute  = Default(String, "Hello")
    required_composite = Required(C1)
    optional_composite = C1
    default_composite  = Default(C1, C1(required_attribute = 1, required_list = ["a", "b"]))

  BASIC_TYPES = [Integer, Float, String, C1, M1]
  LIST_TYPES = map(List, BASIC_TYPES)
  MAP_TYPES = []
  for typ1 in (Integer, C1, M1):
    for typ2 in (String, C1, M1):
      MAP_TYPES.append(Map(typ1,typ2))
  for mt1 in BASIC_TYPES + LIST_TYPES + MAP_TYPES:
    for mt2 in BASIC_TYPES + LIST_TYPES + MAP_TYPES:
      t = Map(mt1, mt2)
      ser = t.serialize_schema()
      serdes = Schema.deserialize_schema(ser)
      serdesser = serdes.serialize_schema()
      assert ser == serdesser, 'Multiple ser/der cycles should not affect types.'
      default = Map(typ1, typ2)({})
      assert Map(typ1, typ2)(default.get()) == default, (
        'Unwrapping/rewrapping should leave values intact')

def test_recursive_unwrapping():
  class Employee(Struct):
    name = Required(String)
    location = Default(String, "San Francisco")
    age = Integer

  class Employer(Struct):
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

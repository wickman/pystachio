import pytest

from pystachio import *


def ref(address):
  return Ref.from_address(address)


def test_basic_schemas():
  BASIC_TYPES = (Integer, Float, String, Boolean)

  for typ in BASIC_TYPES:
    assert TypeFactory.new({}, *typ.serialize_type()) == typ

  for typ in BASIC_TYPES:
    assert isinstance(TypeFactory.new({}, *List(typ).serialize_type())([]), List(typ))

  for typ1 in BASIC_TYPES:
    for typ2 in BASIC_TYPES:
      assert isinstance(TypeFactory.new({}, *Map(typ1, typ2).serialize_type())({}), Map(typ1, typ2))


def test_complex_schemas():
  BASIC_TYPES = (Integer, Float, String, Boolean)
  LIST_TYPES = [List(bt) for bt in BASIC_TYPES]
  MAP_TYPES = []
  ENUM_TYPES = [Enum(), Enum('Red', 'Green', 'Blue'), Enum('Animals', ('Dog', 'Cat'))]
  for typ1 in BASIC_TYPES:
    for typ2 in BASIC_TYPES:
      MAP_TYPES.append(Map(typ1,typ2))
  for mt1 in (BASIC_TYPES, LIST_TYPES, MAP_TYPES, ENUM_TYPES):
    for mt2 in (BASIC_TYPES, LIST_TYPES, MAP_TYPES, ENUM_TYPES):
      for typ1 in mt1:
        for typ2 in mt2:
          assert isinstance(TypeFactory.new({}, *Map(typ1, typ2).serialize_type())({}), Map(typ1, typ2))


def test_composite_schemas_are_not_lossy():
  class C1(Struct):
    required_attribute = Required(Integer)
    optional_attribute = Float
    default_attribute  = Default(String, "Hello")
    required_list      = Required(List(Boolean))
    optional_list      = List(Integer)
    default_list       = Default(List(Float), [1.0, Float(2.0)])
    required_map       = Required(Map(String, Integer))
    optional_map       = Map(Integer, Float)
    default_map        = Default(Map(Boolean, Integer), {True: 2, False: 3})

  class M1(Struct):
    required_attribute = Required(Integer)
    optional_attribute = Float
    default_attribute  = Default(String, "Hello")
    required_composite = Required(C1)
    optional_composite = C1
    default_composite  = Default(C1, C1(required_attribute = 1, required_list = ["a", "b"]))

  BASIC_TYPES = [Integer, Float, String, Boolean, C1, M1]
  LIST_TYPES = [List(bt) for bt in BASIC_TYPES]
  MAP_TYPES = []
  for typ1 in (Integer, C1, M1):
    for typ2 in (String, C1, M1):
      MAP_TYPES.append(Map(typ1,typ2))
  for mt1 in BASIC_TYPES + LIST_TYPES + MAP_TYPES:
    for mt2 in BASIC_TYPES + LIST_TYPES + MAP_TYPES:
      t = Map(mt1, mt2)
      ser = t.serialize_type()
      serdes = TypeFactory.new({}, *ser)
      serdesser = serdes.serialize_type()
      assert ser == serdesser, 'Multiple ser/der cycles should not affect types.'
      default = Map(typ1, typ2)({})
      assert Map(typ1, typ2)(default.get()) == default, (
        'Unwrapping/rewrapping should leave values intact: %s vs %s' % (typ1, typ2))


def test_recursive_unwrapping():
  class Employee(Struct):
    name = Required(String)
    location = Default(String, "San Francisco")
    age = Integer

  class Employer(Struct):
    name = Required(String)
    employees = Default(List(Employee), [Employee(name = 'Bob')])

  new_employer = TypeFactory.new({}, *Employer.serialize_type())
  assert new_employer.serialize_type() == Employer.serialize_type()
  assert isinstance(new_employer(), Employer)
  nontwttr = Employer()
  assert not nontwttr.check().ok()
  repr(nontwttr.check())
  twttr = Employer(name = 'Twitter')
  assert twttr.check().ok()
  repr(twttr.check())


def test_json():
  import os, tempfile

  class Employee(Struct):
    name = Required(String)
    location = Default(String, "San Francisco")
    age = Integer

  class Employer(Struct):
    name = Required(String)
    employees = Default(List(Employee), [Employee(name = 'Bob')])

  try:
    fd, fn = tempfile.mkstemp()
    os.close(fd)

    with open(fn, 'w') as fp:
      Employer.dump(fp)

    namespace = TypeFactory.load_file(fn)
    assert isinstance(namespace['Employer'](), Employer)

  finally:
    os.unlink(fn)


def test_load():
  class Employee(Struct):
    name = Required(String)
    location = Default(String, "San Francisco")
    age = Integer

  class Employer(Struct):
    name = Required(String)
    employees = Default(List(Employee), [Employee(name = 'Bob')])

  employer_type = Employer.serialize_type()
  # It would be swell if I could 'del Employee' here.

  deposit = {}
  TypeFactory.load(employer_type, into=deposit)
  assert 'Employee' in deposit
  assert 'Employer' in deposit

  twttr = deposit['Employer'](name = 'Twitter')
  assert twttr.find(ref('employees[0].name')) == String('Bob')
  assert twttr.find(ref('employees[0].location')) == String('San Francisco')


def test_unimplementeds():
  # coverage-whore
  with pytest.raises(NotImplementedError):
    Type.type_factory()
  with pytest.raises(NotImplementedError):
    Type.type_parameters()
  with pytest.raises(NotImplementedError):
    Type().check()
  with pytest.raises(NotImplementedError):
    Type.serialize_type()

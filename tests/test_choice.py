import json

from pystachio import Choice, Default, Enum, Float, Integer, List, Ref, Required, String, Struct
from pystachio.naming import frozendict


def test_choice_type():
  IntStr = Choice("IntStrFloat", (Integer, String))
  one = IntStr(123)
  two = IntStr("123")
  three = IntStr("abc")
  assert one.unwrap() == Integer(123)
  assert two.unwrap() == Integer(123)
  assert three.unwrap() == String("abc")


def test_choice_error():
  IntFloat = Choice((Integer, Float))
  one = IntFloat(123)
  two = IntFloat(123.456)
  three = IntFloat("123.abc")
  assert one.check().ok()
  assert two.check().ok()
  assert not three.check().ok()


def test_choice_triple():
  Triple = Choice((Integer, Float, String))
  one = Triple(123)
  two = Triple(123.456)
  three = Triple("123.abc")
  assert one.check().ok()
  assert two.check().ok()
  assert three.check().ok()


def test_choice_interpolation():
  IntFloat = Choice((Integer, Float))
  one = IntFloat('{{abc}}')
  two = IntFloat('{{a}}{{b}}')
  one_int = one.bind(abc=34)
  assert isinstance(one_int.interpolate()[0], Integer)
  assert one_int.check().ok()
  one_fl = one.bind(abc=123.354)
  assert isinstance(one_fl.interpolate()[0], Float)
  assert one_fl.check().ok()
  one_str = one.bind(abc="def")
  assert not one_str.check().ok()
  assert two.interpolate()[1] == [Ref.from_address('a'), Ref.from_address('b')]
  two_one =  two.bind(a=12, b=23)
  assert two_one.check().ok()
  assert two_one.unwrap() == Integer(1223)
  two_two = two.bind(a=12, b=".34")
  assert two_two.check().ok()
  assert two_two.unwrap() == Float(12.34)


def test_choice_in_struct():
  class SOne(Struct):
    a = Choice((Integer, Float))
    b = String

  one = SOne(a=12, b="abc")
  assert one.check().ok()
  assert one.interpolate()[0].a().unwrap() == Integer(12)

  two = SOne(a="1{{q}}2", b="hi there")
  assert not two.check().ok()
  refs = two.interpolate()[1]
  assert refs == [Ref.from_address('q')]

  two_int = two.bind(q="34")
  assert two_int.check().ok()
  assert two_int.a().unwrap() == Integer(1342)

  two_fl = two.bind(q="3.4")
  assert two_fl.check().ok()
  assert two_fl.a().unwrap() == Float(13.42)

  two_str = two.bind(q="abc")
  assert not two_str.check().ok()


def test_struct_in_choice_in_struct():
  class Foo(Struct):
    a = String
    b = Integer
  class Yuck(Struct):
    one = Choice([Foo, Integer])
    two = String

  y = Yuck(one=3, two="abc")
  assert y.check().ok()

  z = Yuck(one=Foo(a="1", b=2), two="hello")
  assert z.check().ok()


def test_json_choice():
  """Make sure that serializing to JSON works for structs with choices."""
  class Foo(Struct):
    a = String
    b = Integer
  class Yuck(Struct):
    one = Choice([Foo, Integer])
    two = String

  z = Yuck(one=Foo(a="1", b=2), two="hello")
  assert z.check().ok()

  d = json.loads(z.json_dumps())
  assert d == {"two": "hello", "one": {"a": "1", "b": 2}}


def test_choice_string_enum():
  TestEnum = Enum("TestEnum", ("A", "B", "C"))
  TestChoice = Choice("TestChoice", (TestEnum, String))
  v = TestChoice("A")
  assert isinstance(v.interpolate()[0], TestEnum)
  assert isinstance(TestChoice("Q").interpolate()[0], String)


def test_choice_default():
  """Ensure that choices with a default work correctly."""
  class Dumb(Struct):
    one = String

  class ChoiceDefaultStruct(Struct):
    a = Default(Choice("IntOrDumb", [Dumb, Integer]), 28)
    b = Integer

  class OtherStruct(Struct):
    first = ChoiceDefaultStruct
    second = String

  v = OtherStruct(second="hello")
  assert v.check()
  assert json.loads(v.json_dumps()) == {"second": "hello"}
  w = v(first=ChoiceDefaultStruct())
  assert w.check()
  assert json.loads(w.json_dumps()) == {'first': {'a': 28}, 'second': 'hello'}
  x = v(first=ChoiceDefaultStruct(a=296, b=36))
  assert x.check()
  assert json.loads(x.json_dumps()) == {'first': {'a': 296, 'b': 36},
                      'second': 'hello'}
  y = v(first=ChoiceDefaultStruct(a=Dumb(one="Oops"), b=37))
  assert y.check()
  assert json.loads(y.json_dumps()) == {'first': {'a': {'one': 'Oops'}, 'b': 37},
                                        'second': 'hello'}


def test_choice_primlist():
  """Test that choices with a list value work correctly."""
  C = Choice([String, List(Integer)])
  c = C([1, 2, 3])
  assert c.check().ok()
  c = C("hello")
  assert c.check().ok()
  c = C([1, 2, "{{x}}"])
  assert not c.check().ok()
  assert c.bind(x=3).check().ok()


def test_repr():
  class Dumb(Struct):
    one = String

  class ChoiceDefaultStruct(Struct):
    a = Default(Choice("IntOrDumb", [Dumb, Integer]), 28)
    b = Integer

  class OtherStruct(Struct):
    first = ChoiceDefaultStruct
    second = String

  C = Choice([String, List(Integer)])

  testvalone = C("hello")
  testvaltwo = C([1, 2, 3])
  assert repr(testvalone) == "Choice_String_IntegerList('hello')"
  assert repr(testvaltwo) == "Choice_String_IntegerList([1, 2, 3])"


def test_get_choice_in_struct():
  class Foo(Struct):
    foo = Required(String)

  class Bar(Struct):
    bar = Required(String)

  Item = Choice("Item", (Foo, Bar))

  class Qux(Struct):
    item = Choice([String, List(Item)])

  b = Qux(item=[Foo(foo="fubar")])
  assert b.get() == frozendict({'item': (frozendict({'foo': u'fubar'}),)})

import json
from pystachio import (
    Choice,
    Enum,
    Float,
    Integer,
    Ref,
    String,
    Struct,
)


def test_choice_type():
    IntStr = Choice("IntStrFloat", (Integer, String))
    one = IntStr(123)
    two = IntStr("123")
    three = IntStr("abc")
    assert one.interpolate()[0] == Integer(123)
    assert two.interpolate()[0] == Integer(123)
    assert three.interpolate()[0] == String("abc")


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
    assert two_one.interpolate()[0] == Integer(1223)
    two_two = two.bind(a=12, b=".34")
    assert two_two.check().ok()
    assert two_two.interpolate()[0] == Float(12.34)


def test_choice_in_struct():
    class SOne(Struct):
        a = Choice((Integer, Float))
        b = String

    one = SOne(a=12, b="abc")
    assert one.check().ok()
    assert one.interpolate()[0].a().value() == Integer(12)

    two = SOne(a="1{{q}}2", b="hi there")
    assert not two.check().ok()
    refs = two.interpolate()[1]
    assert refs == [Ref.from_address('q')]

    two_int = two.bind(q="34")
    assert two_int.check().ok()
    assert two_int.a().value() == Integer(1342)

    two_fl = two.bind(q="3.4")
    assert two_fl.check().ok()
    assert two_fl.a().value() == Float(13.42)

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
    print("+++++ %s" + z.json_dumps())
    d = json.loads(z.json_dumps())
    assert d == {"two": "hello", "one": {"a": "1", "b": 2}}

def test_choice_string_enum():
    TestEnum = Enum("TestEnum", ("A", "B", "C"))
    TestChoice = Choice("TestChoice", (TestEnum, String))
    v = TestChoice("A")
    assert isinstance(v.interpolate()[0], TestEnum)
    assert isinstance(TestChoice("Q").interpolate()[0], String)
    assert z.json_dumps() == '{"two": "hello", "one": {"a": "1", "b": 2}}'

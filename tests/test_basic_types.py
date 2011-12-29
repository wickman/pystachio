import pytest
from pystachio.basic import String, Integer, Float, SimpleObject

def unicodey(s):
  from sys import version_info
  if version_info[0] == 2:
    return unicode(s)
  else:
    return s

def test_bad_inputs():
  for typ in Float, Integer, String:
    with pytest.raises(TypeError):
      typ()
    with pytest.raises(TypeError):
      typ("1", "2")
    with pytest.raises(TypeError):
      typ(foo = '123')

    bad_inputs = [ {1:2}, None, type, Float, Integer, String,
                   Float(1), Integer(1), String(1) ]
    for inp in bad_inputs:
      with pytest.raises(SimpleObject.CoercionError):
        '%s' % typ(inp)

def test_string_constructors():
  good_inputs = [
    '', 'a b c', '{{a}} b {{c}}', '%d', unicodey('unic\u215bde should work too, yo!'),
    1.0, 1, 1e3, 1.0e3
  ]

  for input in good_inputs:
    '%s' % String(input)
    repr(String(input))


def test_float_constructors():
  bad_inputs = ['', 'a b c', unicodey('a b c'), unicodey('')]
  good_inputs = [unicodey('{{foo}}'), '1 ', ' 1', unicodey('  1e5'), ' {{herp}}.{{derp}} ', 0, 0.0, 1e5]

  for input in bad_inputs:
    with pytest.raises(SimpleObject.CoercionError):
      '%s' % Float(input)

  for input in good_inputs:
    '%s' % Float(input)
    repr(Float(input))

  assert Float(unicodey(' {{herp}}.{{derp}} ')) % {'herp': 1, 'derp': '2e3'} == Float(1.2e3)
  assert Float(123).check().ok()
  assert Float('123.123').check().ok()
  assert not Float('{{foo}}').check().ok()

def test_integer_constructors():
  bad_inputs = ['', 'a b c', unicodey('a b c'), unicodey(''), '1e5']
  good_inputs = [unicodey('{{foo}}'), '1 ', ' 1', ' {{herp}}.{{derp}} ', 0, 0.0, 1e5]

  for input in bad_inputs:
    with pytest.raises(SimpleObject.CoercionError):
      '%s' % Integer(input)

  for input in good_inputs:
    '%s' % Integer(input)
    repr(Integer(input))

  assert Integer(123).check().ok()
  assert Integer('500').check().ok()
  assert not Integer('{{foo}}').check().ok()

def test_cmp():
  assert not Float(1) == Integer(1)
  assert Float(1) != Integer(1)
  assert not String(1) == Integer(1)
  assert Integer(1) < Integer(2)
  assert Integer(2) > Integer(1)
  assert Integer(1) == Integer(1)
  assert String("a") < String("b")
  assert String("a") == String("a")
  assert String("b") > String("a")
  assert Float(1) < Float(2)
  assert Float(2) > Float(1)
  assert Float(1) == Float(1)
  assert Float(1.1) > Float(1)

  # all types <
  for typ1 in (Float, String, Integer):
    for typ2 in (Float, String, Integer):
      if typ1 != typ2:
        assert typ1(1) < typ2(1)
        assert typ1(1) <= typ2(1)
        assert not typ1(1) > typ2(1)
        assert not typ1(1) >= typ2(1)


def test_hash():
  map = {
    Integer(1): 'foo',
    String("bar"): 'baz',
    Float('{{herp}}'): 'derp'
  }
  assert Integer(1) in map
  assert String("bar") in map
  assert Float('{{herp}}') in map
  assert Float('{{derp}}') not in map
  assert Integer(2) not in map
  assert String("baz") not in map

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


def test_float_constructors():
  bad_inputs = ['', 'a b c', unicodey('a b c'), unicodey('')]
  good_inputs = [unicodey('{{foo}}'), '1 ', ' 1', unicodey('  1e5'), ' {{herp}}.{{derp}} ', 0, 0.0, 1e5]

  for input in bad_inputs:
    with pytest.raises(SimpleObject.CoercionError):
      '%s' % Float(input)

  for input in good_inputs:
    '%s' % Float(input)

  assert Float(unicodey(' {{herp}}.{{derp}} ')) % {'herp': 1, 'derp': '2e3'} == Float(1.2e3)


def test_integer_constructors():
  bad_inputs = ['', 'a b c', unicodey('a b c'), unicodey(''), '1e5']
  good_inputs = [unicodey('{{foo}}'), '1 ', ' 1', ' {{herp}}.{{derp}} ', 0, 0.0, 1e5]

  for input in bad_inputs:
    with pytest.raises(SimpleObject.CoercionError):
      '%s' % Integer(input)

  for input in good_inputs:
    '%s' % Integer(input)

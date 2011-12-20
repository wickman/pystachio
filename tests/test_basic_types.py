import pytest
import unittest
from pystachio import (
  String,
  Integer,
  Float,
  Environment)
from pystachio.objects import Object

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
      with pytest.raises(Object.CoercionError):
        '%s' % typ(inp)

def test_string_constructors():
  good_inputs = [
    '', 'a b c', '{{a}} b {{c}}', '%d', u'unic\xf3de should work too, yo!',
    1.0, 1, 1e3, 1.0e3
  ]

  for input in good_inputs:
    '%s' % String(input)


def test_float_constructors():
  bad_inputs = ['', 'a b c', u'a b c', u'']
  good_inputs = [u'{{foo}}', '1 ', ' 1', u'  1e5', ' {{herp}}.{{derp}} ', 0, 0.0, 1e5]

  for input in bad_inputs:
    with pytest.raises(Object.CoercionError):
      '%s' % Float(input)

  for input in good_inputs:
    '%s' % Float(input)

  assert Float(u' {{herp}}.{{derp}} ') % Environment(
    herp = 1,
    derp = '2e3') == Float(1.2e3)


def test_integer_constructors():
  bad_inputs = ['', 'a b c', u'a b c', u'', '1e5']
  good_inputs = [u'{{foo}}', '1 ', ' 1', ' {{herp}}.{{derp}} ', 0, 0.0, 1e5]

  for input in bad_inputs:
    with pytest.raises(Object.CoercionError):
      '%s' % Integer(input)

  for input in good_inputs:
    '%s' % Integer(input)

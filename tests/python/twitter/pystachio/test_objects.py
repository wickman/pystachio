import pytest
import unittest
from twitter.pystachio import (
  ObjectEnvironment,
  ObjectMustacheParser,
  ObjectId)

def test_basic_constructors():
  oe = ObjectEnvironment(a = 1, b = 2)
  assert oe == {'a': 1, 'b': 2}

  oe = ObjectEnvironment({'a': 1, 'b': 2})
  assert oe == {'a': 1, 'b': 2}

  oe = ObjectEnvironment({'a': 1}, b = 2)
  assert oe == {'a': 1, 'b': 2}

  oe = ObjectEnvironment({'a': 1}, a = 2)
  assert oe == {'a': 2}, "last update should win"
  
  oe = ObjectEnvironment({'b': 1}, a = 2)
  assert oe == {'a': 2, 'b': 1}


def test_basic_mustache_splitting():
  assert ObjectMustacheParser.split("{{foo}}") == [ObjectId("foo")]
  assert ObjectMustacheParser.split("{{&foo}}") == ["{{foo}}"]
  splits = ObjectMustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  assert splits == ['blech ', ObjectId("foo"), ' ', ObjectId('bar'), ' bonk ', '{{baz}}', ' bling']


def test_basic_interpolation():
  oe = ObjectEnvironment(a = 1)
  assert ObjectId.interpolate(ObjectId("a"), oe) == 1
  
  oe = ObjectEnvironment(a = {'b': 1})
  assert ObjectId.interpolate(ObjectId("a.b"), oe) == 1
  assert oe == {'a': {'b': 1}}
  
  oe = ObjectEnvironment(a = {'b': 1})
  assert ObjectId.interpolate(ObjectId("a.b"), oe) == 1
  assert oe == {'a': {'b': 1}}

"""

from twitter.pystachio import Object
from twitter.pystachio.types import Float, Integer, String

class Resources(Object):
  cpu = Float(required=True)
  ram = Integer(required=True)
  disk = Integer

class Process(Object):
  name = String(required=True)
  min_resources = Resources
  max_resources = Resources(required=True)

r = Resources(cpu = 1.0, disk = 1000)
p = Process(name = "hello_world", min_resources = r)


"""  
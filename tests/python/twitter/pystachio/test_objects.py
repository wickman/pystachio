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

  oe2 = ObjectEnvironment(oe, b = 2)
  assert oe2 == {'a': 2, 'b': 2}


def test_selective_merge():
  oe1 = ObjectEnvironment(a = 1, b = 2)
  oe2 = ObjectEnvironment(a = 1, b = {'c': 2})
  ObjectEnvironment.merge(oe1, oe2)
  assert oe1 == { 'a': 1, 'b': { 'c': 2 } }

  oe1 = ObjectEnvironment(a = 1, b = 2)
  oe2 = ObjectEnvironment(a = 1, b = {'c': 2})
  ObjectEnvironment.merge(oe2, oe1)
  assert oe1 == { 'a': 1, 'b': 2 }

  oe1 = ObjectEnvironment(a = { 'b': 1 })
  oe2 = ObjectEnvironment(a = { 'c': 2 })
  ObjectEnvironment.merge(oe1, oe2)
  assert oe1 == { 'a': {'b': 1, 'c': 2 } }


def test_basic_mustache_splitting():
  assert ObjectMustacheParser.split("{{foo}}") == [ObjectId("foo")]
  assert ObjectMustacheParser.split("{{&foo}}") == ["{{foo}}"]
  splits = ObjectMustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  assert splits == ['blech ', ObjectId("foo"), ' ', ObjectId('bar'), ' bonk ', '{{baz}}', ' bling']


def test_basic_mustache_joining():
  oe = ObjectEnvironment(foo = "foo herp",
                         bar = "bar derp",
                         baz = "baz blerp")

  joined, unbound = ObjectMustacheParser.join(ObjectMustacheParser.split("{{foo}}"), oe)
  assert joined == "foo herp"
  assert unbound == []

  splits = ObjectMustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  joined, unbound = ObjectMustacheParser.join(splits, oe)
  assert joined == 'blech foo herp bar derp bonk {{baz}} bling'
  assert unbound == []

  splits = ObjectMustacheParser.split('{{foo}} {{bar}} {{unbound}}')
  with pytest.raises(ObjectId.UnboundObjectId):
    ObjectMustacheParser.join(splits, oe)
  joined, unbound = ObjectMustacheParser.join(splits, oe, strict=False)
  assert joined == 'foo herp bar derp {{unbound}}'
  assert unbound == [ObjectId('unbound')]


def test_basic_interpolation():
  oe = ObjectEnvironment(a = 1)
  assert ObjectId.interpolate(ObjectId("a"), oe) == 1

  oe = ObjectEnvironment(a = {'b': 1})
  assert ObjectId.interpolate(ObjectId("a.b"), oe) == 1
  assert oe == {'a': {'b': 1}}

  oe = ObjectEnvironment(a = {'b': 1})
  assert ObjectId.interpolate(ObjectId("a.b"), oe) == 1
  assert oe == {'a': {'b': 1}}

  oe = ObjectEnvironment(a = {'b': {'c': 1}, 'c': ObjectEnvironment(d = 2)})
  assert ObjectId.interpolate(ObjectId("a.b"), oe) == {'c': 1}
  assert ObjectId.interpolate(ObjectId("a.b.c"), oe) == 1
  assert ObjectId.interpolate(ObjectId("a.c"), oe) == {'d': 2}
  assert ObjectId.interpolate(ObjectId("a.c.d"), oe) == 2





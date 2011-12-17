import pytest
import unittest
from twitter.pystachio import (
  Environment,
  MustacheParser,
  Ref)

def test_basic_constructors():
  oe = Environment(a = 1, b = 2)
  assert oe == {'a': 1, 'b': 2}

  oe = Environment({'a': 1, 'b': 2})
  assert oe == {'a': 1, 'b': 2}

  oe = Environment({'a': 1}, b = 2)
  assert oe == {'a': 1, 'b': 2}

  oe = Environment({'a': 1}, a = 2)
  assert oe == {'a': 2}, "last update should win"

  oe = Environment({'b': 1}, a = 2)
  assert oe == {'a': 2, 'b': 1}

  oe2 = Environment(oe, b = 2)
  assert oe2 == {'a': 2, 'b': 2}


def test_selective_merge():
  oe1 = Environment(a = 1, b = 2)
  oe2 = Environment(a = 1, b = {'c': 2})
  Environment.merge(oe1, oe2)
  assert oe1 == { 'a': 1, 'b': { 'c': 2 } }

  oe1 = Environment(a = 1, b = 2)
  oe2 = Environment(a = 1, b = {'c': 2})
  Environment.merge(oe2, oe1)
  assert oe1 == { 'a': 1, 'b': 2 }

  oe1 = Environment(a = { 'b': 1 })
  oe2 = Environment(a = { 'c': 2 })
  Environment.merge(oe1, oe2)
  assert oe1 == { 'a': {'b': 1, 'c': 2 } }


def test_basic_mustache_splitting():
  assert MustacheParser.split("{{foo}}") == [Ref("foo")]
  assert MustacheParser.split("{{&foo}}") == ["{{foo}}"]
  splits = MustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  assert splits == ['blech ', Ref("foo"), ' ', Ref('bar'), ' bonk ', '{{baz}}', ' bling']


def test_basic_mustache_joining():
  oe = Environment(foo = "foo herp",
                         bar = "bar derp",
                         baz = "baz blerp")

  joined, unbound = MustacheParser.join(MustacheParser.split("{{foo}}"), oe)
  assert joined == "foo herp"
  assert unbound == []

  splits = MustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  joined, unbound = MustacheParser.join(splits, oe)
  assert joined == 'blech foo herp bar derp bonk {{baz}} bling'
  assert unbound == []

  splits = MustacheParser.split('{{foo}} {{bar}} {{unbound}}')
  with pytest.raises(Ref.UnboundRef):
    MustacheParser.join(splits, oe)
  joined, unbound = MustacheParser.join(splits, oe, strict=False)
  assert joined == 'foo herp bar derp {{unbound}}'
  assert unbound == [Ref('unbound')]


def test_basic_interpolation():
  oe = Environment(a = 1)
  assert Ref.lookup(Ref("a"), oe) == 1

  oe = Environment(a = {'b': 1})
  assert Ref.lookup(Ref("a.b"), oe) == 1
  assert oe == {'a': {'b': 1}}

  oe = Environment(a = {'b': 1})
  assert Ref.lookup(Ref("a.b"), oe) == 1
  assert oe == {'a': {'b': 1}}

  oe = Environment(a = {'b': {'c': 1}, 'c': Environment(d = 2)})
  assert Ref.lookup(Ref("a.b"), oe) == {'c': 1}
  assert Ref.lookup(Ref("a.b.c"), oe) == 1
  assert Ref.lookup(Ref("a.c"), oe) == {'d': 2}
  assert Ref.lookup(Ref("a.c.d"), oe) == 2

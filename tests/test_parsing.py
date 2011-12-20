import pytest
import unittest

from pystachio import (
  Environment,
  MustacheParser,
  Ref,
  List,
  Map,
  String)

def test_mustache_re():
  # valid ref names
  assert MustacheParser.split("{{foo}}") == [Ref("foo")]
  assert MustacheParser.split("{{_}}") == [Ref("_")]
  with pytest.raises(Ref.InvalidRefError):
    MustacheParser.split("{{4}}")
  def chrange(a,b):
    return ''.join(map(lambda ch: str(chr(ch)), range(ord(a), ord(b)+1)))
  slash_w = chrange('a','z') + chrange('A','Z') + chrange('0','9') + '_'
  assert MustacheParser.split("{{%s}}" % slash_w) == [Ref(slash_w)]

  # bracketing
  assert MustacheParser.split("{{{foo}}") == ['{', Ref('foo')]
  assert MustacheParser.split("{{foo}}}") == [Ref('foo'), '}']
  assert MustacheParser.split("{{{foo}}}") == ['{', Ref('foo'), '}']
  assert MustacheParser.split("{{}}") == ['{{}}']
  assert MustacheParser.split("{{{}}}") == ['{{{}}}']
  assert MustacheParser.split("{{{{foo}}}}") == ['{{', Ref("foo"), '}}']

  invalid_refs = ['!@', '-', '$', ':']
  for ref in invalid_refs:
    with pytest.raises(Ref.InvalidRefError):
      print MustacheParser.split("{{%s}}" % ref)

def test_mustache_splitting():
  assert MustacheParser.split("{{foo}}") == [Ref("foo")]
  assert MustacheParser.split("{{&foo}}") == ["{{foo}}"]
  splits = MustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  assert splits == ['blech ', Ref("foo"), ' ', Ref('bar'), ' bonk ', '{{baz}}', ' bling']

def test_mustache_joining():
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
  with pytest.raises(MustacheParser.Uninterpolatable):
    MustacheParser.join(splits, oe)
  joined, unbound = MustacheParser.join(splits, oe, strict=False)
  assert joined == 'foo herp bar derp {{unbound}}'
  assert unbound == [Ref('unbound')]

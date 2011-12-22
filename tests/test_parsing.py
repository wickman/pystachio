import pytest

from pystachio.parsing import MustacheParser
from pystachio.naming import Ref
from pystachio.base import Environment

def ref(address):
  return Ref.from_address(address)

def test_mustache_re():
  assert MustacheParser.split("{{foo}}") == [ref("foo")]
  assert MustacheParser.split("{{_}}") == [ref("_")]
  with pytest.raises(Ref.InvalidRefError):
    MustacheParser.split("{{4}}")
  def chrange(a,b):
    return ''.join(map(lambda ch: str(chr(ch)), range(ord(a), ord(b)+1)))
  slash_w = chrange('a','z') + chrange('A','Z') + chrange('0','9') + '_'
  assert MustacheParser.split("{{%s}}" % slash_w) == [ref(slash_w)]

  # bracketing
  assert MustacheParser.split("{{{foo}}") == ['{', ref('foo')]
  assert MustacheParser.split("{{foo}}}") == [ref('foo'), '}']
  assert MustacheParser.split("{{{foo}}}") == ['{', ref('foo'), '}']
  assert MustacheParser.split("{{}}") == ['{{}}']
  assert MustacheParser.split("{{{}}}") == ['{{{}}}']
  assert MustacheParser.split("{{{{foo}}}}") == ['{{', ref("foo"), '}}']

  invalid_refs = ['!@', '-', '$', ':']
  for val in invalid_refs:
    with pytest.raises(Ref.InvalidRefError):
      print MustacheParser.split("{{%s}}" % val)

def test_mustache_splitting():
  assert MustacheParser.split("{{foo}}") == [ref("foo")]
  assert MustacheParser.split("{{&foo}}") == ["{{foo}}"]
  splits = MustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  assert splits == ['blech ', ref("foo"), ' ', ref('bar'), ' bonk ', '{{baz}}', ' bling']

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
  assert unbound == [Ref.from_address('unbound')]

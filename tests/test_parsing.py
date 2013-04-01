import pytest

from pystachio.base import Environment
from pystachio.basic import String
from pystachio.composite import Struct, Required, Default
from pystachio.container import List
from pystachio.naming import Ref
from pystachio.parsing import MustacheParser


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
      MustacheParser.split("{{%s}}" % val)


def test_mustache_splitting():
  assert MustacheParser.split("{{foo}}") == [ref("foo")]
  assert MustacheParser.split("{{&foo}}") == ["{{&foo}}"]
  assert MustacheParser.split("{{&foo}}", downcast=True) == ["{{foo}}"]
  splits = MustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  assert splits == ['blech ', ref("foo"), ' ', ref('bar'), ' bonk {{&baz}} bling']
  splits = MustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling', downcast=True)
  assert splits == ['blech ', ref("foo"), ' ', ref('bar'), ' bonk {{baz}} bling']


def test_mustache_joining():
  oe = Environment(foo = "foo herp",
                   bar = "bar derp",
                   baz = "baz blerp")

  joined, unbound = MustacheParser.join(MustacheParser.split("{{foo}}"), oe)
  assert joined == "foo herp"
  assert unbound == []

  splits = MustacheParser.split('blech {{foo}} {{bar}} bonk {{&baz}} bling')
  joined, unbound = MustacheParser.join(splits, oe)
  assert joined == 'blech foo herp bar derp bonk {{&baz}} bling'
  assert unbound == []

  splits = MustacheParser.split('{{foo}} {{bar}} {{unbound}}')
  joined, unbound = MustacheParser.join(splits, oe)
  assert joined == 'foo herp bar derp {{unbound}}'
  assert unbound == [Ref.from_address('unbound')]


def test_nested_mustache_resolution():
  # straight
  oe = Environment(foo = '{{bar}}', bar = '{{baz}}', baz = 'hello')
  for pattern in ('{{foo}}', '{{bar}}', '{{baz}}', 'hello'):
    resolved, unbound = MustacheParser.resolve('%s world' % pattern, oe)
    assert resolved == 'hello world'
    assert unbound == []

  # in structs
  class Process(Struct):
    name = Required(String)
    cmdline = String

  class Task(Struct):
    name = Default(String, '{{processes[0].name}}')
    processes = List(Process)

  task = Task(processes = [Process(name="hello"), Process(name="world")])
  assert task.name().get() == 'hello'

  # iterably
  resolve_string = '{{foo[{{bar}}]}}'
  resolve_list = List(String)(["hello", "world"])
  resolved, unbound = MustacheParser.resolve(resolve_string, Environment(foo=resolve_list, bar=0))
  assert resolved == 'hello'
  assert unbound == []
  resolved, unbound = MustacheParser.resolve(resolve_string, Environment(foo=resolve_list, bar="0"))
  assert resolved == 'hello'
  assert unbound == []
  resolved, _ = MustacheParser.resolve(resolve_string, Environment(foo=resolve_list, bar=1))
  assert resolved == 'world'
  resolved, unbound = MustacheParser.resolve(resolve_string, Environment(foo=resolve_list, bar=2))
  assert resolved == '{{foo[2]}}'
  assert unbound == [ref('foo[2]')]


def test_mustache_resolve_cycles():
  with pytest.raises(MustacheParser.Uninterpolatable):
    MustacheParser.resolve('{{foo[{{bar}}]}} {{baz}}',
       Environment(foo = List(String)(["{{foo[{{bar}}]}}", "world"])), Environment(bar = 0))


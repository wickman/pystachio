from pystachio import *
from pystachio.matcher import Any, Matcher


def test_matcher():
  matcher = Matcher('hello')
  assert list(matcher.match(String(''))) == []
  assert list(matcher.match(String('hello'))) == []
  assert list(matcher.match(String('{{hello}}'))) == [('hello',)]

  matcher = Matcher('packer')[Any][Any][Any]
  matches = list(matcher.match(String('{{packer[foo][bar][baz].bak}}')))
  assert len(matches) == 1
  assert matches[0] == ('packer', 'foo', 'bar', 'baz')

  matcher = Matcher('derp').Any[r'\d+']
  matches = list(matcher.match(String('{{derp.a[23]}}')))
  assert len(matches) == 1
  assert matches[0] == ('derp', 'a', '23')

  matcher = Matcher('herp').derp
  assert list(matcher.match(String('{{herp.derp}}'))) == [('herp', 'derp')]

  matcher = Matcher('herp')._('.*')
  assert list(matcher.match(String('{{herp.derp}}'))) == [('herp', 'derp')]


def test_negative_matches():
  matcher = Matcher('hello')
  assert list(matcher.match(String('{{not_hello}}'))) == []

  matcher = Matcher('a').b.c
  assert list(matcher.match(String('{{a.b.d}}'))) == []


def test_binder():
  class Packer(Struct):
    target = Required(String)

  packer_matcher = Matcher('packer')[Any][Any][Any]

  def packer_binder(_, role, env, name):
    return Packer(target = '{{role}}/{{env}}/{{name}}').bind(role=role, env=env, name=name)

  assert str(packer_matcher.apply(packer_binder, String('{{packer[foo][bar][baz].target}}'))) == (
      'foo/bar/baz')

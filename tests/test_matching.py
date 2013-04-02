import copy

from pystachio import *
from pystachio.matcher import Matcher, Any


def test_matcher():
  packer_matcher = Matcher("packer")[Any][Any][Any]

  def replacer(ref, namables, _, role, app, version):
    namables = list(namables)
    namables.append(Environment({
      Ref.from_address("packer[%s][%s][%s]" % (role, app, version)): {'bak': 'hello'}}
    ))
    return ref, namables

  joined, refs = String('{{packer[foo][bar][baz].bak}}').interpolate((packer_matcher >> replacer,))
  assert joined == String('hello')
  assert refs == []



def test_ignore():
  thermos_matcher = Matcher("thermos")

  def replacer(ref, namables, root):
    thermos_ref = Ref(copy.copy(ref.components()))
    thermos_ref._components[0] = Ref.Dereference('&' + root)
    return thermos_ref, namables

  joined, refs = String('{{thermos.bork}}').interpolate((thermos_matcher >> replacer,))
  assert joined == String('{{thermos.bork}}')
  assert refs == []

from .compatibility import Compatibility
from .naming import Ref


class ObjectProxy(object):
  class InterpolationError(Exception): pass

  __slots__ = ('_fragments', '_target_cls')

  @classmethod
  def resolve_fragment(cls, fragment, scopes):
    if not isinstance(fragment, Ref):
      return fragment
    for scope in scopes:
      try:
        return scope.find(fragment)
      except scope.NotFound:
        continue
    return fragment

  def __init__(self, fragments, target_cls):
    self._fragments = fragments
    self._target_cls = target_cls

  def interpolate(self, scopes):
    fragments = [self.resolve_fragment(fragment, scopes) for fragment in self._fragments]
    if len(fragments) == 1:
      if isinstance(fragments[0], self._target_cls):
        return fragments[0].in_scope(*scopes).interpolate()
    return (''.join(Compatibility.to_str(fragment) for fragment in fragments),
        [fragment for fragment in fragments if isinstance(fragment, Ref)])

  def __str__(self):
    return ''.join(Compatibility.to_str(fragment) for fragment in self._fragments)

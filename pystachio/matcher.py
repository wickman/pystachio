import copy
import re

from .compatibility import Compatibility
from .naming import Ref

try:
  from itertools import izip_longest as zipl
except ImportError:
  from itertools import zip_longest as zipl



class Any(object):
  pass


class Matcher(object):
  """
    Matcher of Ref patterns.
  """

  __slots__ = ('_components', '_resolver')

  class Error(Exception): pass
  class NoMatch(Error): pass

  @classmethod
  def escape(cls, pattern):
    if not pattern.endswith('$'):
      pattern = pattern + '$'
    if not pattern.startswith('^'):
      pattern = '^' + pattern
    return re.compile(pattern)

  def __init__(self, root=None):
    if root is None:
      self._components = []
      return
    if not isinstance(root, Compatibility.stringy) and root is not Any:
      raise ValueError('Invalid root match value: %s' % root)
    self._components = [Ref.Dereference(self.escape('.*' if root is Any else root))]

  def __extend(self, value):
    new_match = Matcher()
    new_match._components = copy.copy(self._components) + [value]
    return new_match

  def __getattr__(self, pattern):
    if pattern == '_':
      return lambda pattern: self.__extend(Ref.Dereference(self.escape(pattern)))
    elif pattern == 'Any':
      return self.__extend(Ref.Dereference(self.escape('.*')))
    else:
      return self.__extend(Ref.Dereference(self.escape(pattern)))

  def __getitem__(self, pattern):
    if pattern is Any:
      return self.__extend(Ref.Index(self.escape('.*')))
    else:
      return self.__extend(Ref.Index(self.escape(pattern)))

  def __repr__(self):
    return 'Match(%s)' % '+'.join(map(str, self._components))

  def match(self, pystachio_object):
    _, refs = pystachio_object.interpolate()
    for ref in refs:
      args = []
      zips = list(zipl(self._components, ref.components()))
      for pattern, component in zips[:len(self._components)]:
        if pattern.__class__ != component.__class__ or not pattern.value.match(component.value):
          break
        args.append(component.value)
      else:
        yield tuple(args)

  def __translate(self, match_tuple):
    components = []
    for component, match in zip(self._components, match_tuple):
      components.append(component.__class__(match))
    return Ref(components)

  def apply(self, binder, pystachio_object):
    if not callable(binder):
      raise TypeError('binder must be a callable')
    for match in self.match(pystachio_object):
      pystachio_object = pystachio_object.bind({self.__translate(match): binder(*match)})
    return pystachio_object

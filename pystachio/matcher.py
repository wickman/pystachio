# Match("name")._('.*')._.instance >> mutator
#
# def apply(ref, object):
#   pass
#

import copy
try:
  from itertools import izip_longest as zipl
except ImportError:
  from itertools import zip_longest as zipl
import re

from .compatibility import Compatibility
from .naming import Namable, Ref


class Any(object):
  pass


class Matcher(object):
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
    self._resolver = None
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

  def __with_resolver(self, resolver):
    new_match = Matcher()
    new_match._components = copy.copy(self._components)
    new_match._resolver = resolver
    return new_match

  def __getattr__(self, pattern):
    if pattern == '_':
      # XXX check
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
    return 'Match(%s%s)' % (
        '+'.join(map(str, self._components)),
        '' if self._resolver is None else ' :: %s' % self._resolver)

  def __rshift__(self, resolver):
    # XXX check
    return self.__with_resolver(resolver)

  def apply(self, ref, namables):
    args = []
    zips = list(zipl(self._components, ref.components()))
    for pattern, component in zips[:len(self._components)]:
      if pattern.__class__ == component.__class__ and pattern.value.match(component.value):
        args.append(component.value)
      else:
        raise self.NoMatch
    value = self._resolver(ref, namables, *args)
    if not hasattr(value, '__iter__') and len(value) != 2:
      raise ValueError('Matcher resolver needs to return an updated ref and namables')
    new_ref, namables = value
    if not isinstance(new_ref, Compatibility.stringy) and not isinstance(new_ref, Ref):
      raise ValueError('Matcher resolver expeced ref, got %s' % new_ref)
    if not hasattr(namables, '__iter__'):
      raise ValueError('Matcher resolver should return array of namables.')
    for namable in namables:
      if not isinstance(namable, Namable):
        raise ValueError('Matcher resolver should return array of namables.')
    return new_ref, namables

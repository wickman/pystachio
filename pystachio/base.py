import copy
from pprint import pformat

from .compatibility import Compatibility
from .naming import Namable, Ref
from .parsing import MustacheParser
from .typing import TypeCheck


class Environment(Namable):
  """
    A mount table for Refs pointing to Objects or arbitrary string substitutions.
  """
  __slots__ = ('_table',)

  @staticmethod
  def wrap(value):
    if isinstance(value, dict):
      return Environment(value)
    elif isinstance(value, (Environment, Object)):
      return value
    else:
      if isinstance(value, Compatibility.numeric + Compatibility.stringy):
        return str(value)
      else:
        raise ValueError(
          'Environment values must be strings, numbers, Objects or other Environments. '
          'Got %s instead.' % type(value))

  def _assimilate_dictionary(self, d):
    for key, val in d.items():
      val = Environment.wrap(val)
      rkey = Ref.wrap(key)
      if isinstance(val, Environment):
        for vkey, vval in val._table.items():
          self._table[rkey + vkey] = vval
      else:
        self._table[rkey] = val

  def _assimilate_table(self, mt):
    for key, val in mt._table.items():
      self._table[key] = val

  def __init__(self, *dicts, **kw):
    self._table = {}
    for d in list(dicts) + [kw]:
      if isinstance(d, dict):
        self._assimilate_dictionary(d)
      elif isinstance(d, Environment):
        self._assimilate_table(d)
      else:
        raise ValueError("Environment expects dict or Environment, got %s" % repr(d))

  def find(self, ref):
    if ref in self._table:
      return self._table[ref]
    targets = [key for key in self._table if Ref.subscope(key, ref)]
    if not targets:
      raise Namable.NotFound(self, ref)
    else:
      for key in sorted(targets, reverse=True):
        scope = self._table[key]
        if not isinstance(scope, Namable):
          continue
        subscope = Ref.subscope(key, ref)
        # If subscope is empty, then we should've found it in the ref table.
        assert not subscope.is_empty()
        try:
          resolved = scope.find(subscope)
          return resolved
        except Namable.Error:
          continue
    raise Namable.NotFound(self, ref)

  def __repr__(self):
    return 'Environment(%s)' % pformat(self._table)


class ObjectFragment(object):
  class InterpolationError(Exception): pass

  __slots__ = ('_fragments', '_target_cls')

  @classmethod
  def resolve_fragment(cls, fragment, scopes):
    if not isinstance(fragment, Ref):
      return fragment
    for scope in scopes:
      try:
        return scope.find(fragment)
      except scope.NamableError:
        continue
    return fragment

  def __init__(self, fragments, target_cls):
    self._fragments = fragments
    self._target_cls = target_cls

  def interpolate(self, scopes):
    fragments = [self.resolve_fragment(fragment, scopes) for fragment in self._fragments]
    if len(fragments) == 1:
      if isinstance(fragments[0], self._target_cls):
        return fragments[0], []
    return (''.join(Compatibility.to_str(fragment) for fragment in fragments),
        [fragment for fragment in fragments if isinstance(fragment, Ref)])
    

class Object(object):
  """
    Object base class, encapsulating a set of variable bindings scoped to this object.
  """
  __slots__ = ('_scopes', '_value')

  class CoercionError(ValueError):
    def __init__(self, src, dst, message=None):
      error = "Cannot coerce '%s' to %s" % (src, dst.__name__)
      ValueError.__init__(self, '%s: %s' % (error, message) if message else error)

  class InterpolationError(Exception): pass

  @classmethod
  def translate_to_scopes(cls, *args, **kw):
    scopes = [arg if isinstance(arg, Namable) else Environment.wrap(arg) for arg in args]
    if kw:
      scopes.append(Environment(kw))
    return tuple(scopes)

  @classmethod
  def coerce(cls, obj):
    """Coerce the given object into the required type.  Raises CoercionError on incompatible
       objects."""
    return obj

  @classmethod
  def unwrap(cls, *args, **kw):
    """Convert constructor argument into a value."""
    raise NotImplementedError

  @classmethod
  def apply(cls, *args, **kw):
    if len(args) == 1 and isinstance(args[0], Compatibility.stringy):
      return ObjectFragment(MustacheParser.split(args[0], keep_aliases=True), cls)
    return cls.unwrap(*args, **kw)
  
  def __init__(self, *args, **kw):
    self._value = self.apply(*args, **kw)
    self._scopes = ()

  def get(self):
    if isinstance(self._value, ObjectFragment):
      resolved, refs = self._value.interpolate(self.scopes())
    else:
      resolved, refs = self.interpolate()
    return resolved if refs else self.coerce(resolved._value)

  def __hash__(self):
    si, _ = self.interpolate()
    return hash(si.get())

  def __copy__(self):
    """
      Return a copy of this object.
    """
    self_copy = self.__class__.__new__(self.__class__)
    self_copy._value = copy.copy(self._value)
    self_copy._scopes = copy.copy(self._scopes)
    return self_copy

  def copy(self):
    return copy.copy(self)

  def bind(self, *args, **kw):
    """
      Bind environment variables into this object's scope.
    """
    new_self = self.copy()
    new_scopes = self.translate_to_scopes(*args, **kw)
    new_self._scopes = tuple(reversed(new_scopes)) + new_self._scopes
    return new_self

  def in_scope(self, *args, **kw):
    """
      Scope this object to a parent environment (like bind but reversed.)
    """
    new_self = self.copy()
    new_scopes = self.translate_to_scopes(*args, **kw)
    new_self._scopes = new_self._scopes + new_scopes
    return new_self

  def scopes(self):
    return self._scopes

  def __ne__(self, other):
    return not (self == other)

  def __mod__(self, namable):
    if isinstance(namable, dict):
      namable = Environment.wrap(namable)
    interp, _ = self.bind(namable).interpolate()
    return interp

  def interpolate(self):
    """
      Interpolate this object in the context of the Object's environment.

      Should return a 2-tuple:
        The object with as much interpolated as possible.
        The remaining unbound Refs necessary to fully interpolate the object.

      If the object is fully interpolated, it should be typechecked prior to
      return.
    """
    raise NotImplementedError

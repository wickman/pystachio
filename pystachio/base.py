import copy
from pprint import pformat

from .compatibility import Compatibility
from .naming import Namable, Ref
from .parsing import MustacheParser
from .typing import TypeCheck

"""


New model:

Standardize on ._value

classmethod .apply(*args, **kw) => value
classmethod .unapply(value)     => frozen/reified version of class
            .copy()             => copy of this object

==> consistent __init__ method across all objects


.unapply can raise:
  CoercionError
  UndefinedRefsError


"""

class Environment(Namable):
  """
    A mechanism to scope namables against Refs.

    For example, Lists, Maps and Structs are all Namables, but rather than bind them
    at a global scope, Environments allow you to bind them to arbitrary scopes rooted
    at a particular Ref.

    Think of it as the mount table for namables in pystachio.
  """
  __slots__ = ('_table',)

  @classmethod
  def wrap(cls, value):
    if isinstance(value, dict):
      return cls(value)
    elif isinstance(value, (cls, Object)):
      return value
    else:
      if isinstance(value, Compatibility.numeric + Compatibility.stringy):
        return str(value)
      else:
        raise ValueError(
          'Environment values must be strings, numbers, Objects or other Environments. '
          'Got %s instead.' % type(value))

  def __init__(self, *dicts, **kw):
    self._table = {}
    for d in list(dicts) + [kw]:
      if isinstance(d, dict):
        self._assimilate_dictionary(d)
      elif isinstance(d, Environment):
        self._assimilate_table(d)
      else:
        raise ValueError("Environment expects dict or Environment, got %s" % repr(d))

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
        except Namable.Error as e:
          continue
    raise Namable.NotFound(self, ref)

  def __repr__(self):
    return 'Environment(%s)' % pformat(self._table)


class Object(object):
  """
    Object base class, encapsulating a set of variable bindings scoped to this object.
  """
  __slots__ = ('_value', '_scopes',)

  class CoercionError(ValueError):
    def __init__(self, src, dst, message=None):
      error = "Cannot coerce '%s' to %s" % (src, dst.__name__)
      ValueError.__init__(self, '%s: %s' % (error, message) if message else error)

  @staticmethod
  def translate_to_scopes(*args, **kw):
    scopes = [arg if isinstance(arg, Namable) else Environment.wrap(arg)
              for arg in args]
    if kw:
      scopes.append(Environment(kw))
    return tuple(scopes)

  @classmethod
  def checker(cls, obj):
    raise NotImplementedError

  @classmethod
  def apply(cls, *args, **kw):
    """
      Convert constructor arguments to an internal value
    """
    raise NotImplementedError

  @classmethod
  def unapply(cls, value):
    """
      Unconvert a value to a frozen representation.
    """
    raise NotImplementedError

  def __init__(self, *args, **kw):
    self._value = self.apply(*args, **kw)
    self._scopes = ()

  def get(self):
    return self.unapply(self._value)

  def __hash__(self):
    si, _ = self.interpolate()
    return hash(si.get())

  def __copy__(self):
    self_copy = self.__class__.__new__(self.__class__)
    self_copy._value = copy.copy(self._value)
    self_copy._scopes = copy.copy(self._scopes)
    return self_copy

  def copy(self):
    """
      Return a copy of this object.
    """
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
    new_scopes = Object.translate_to_scopes(*args, **kw)
    new_self._scopes = new_self._scopes + new_scopes
    return new_self

  def scopes(self):
    return self._scopes

  def check(self):
    """
      Type check this object.
    """
    try:
      si, uninterp = self.interpolate()
    # TODO(wickman) Fully push the MustacheParser considerations to SimpleObjects
    except (Object.CoercionError, MustacheParser.Uninterpolatable) as e:
      return TypeCheck(False, "Unable to interpolate: %s" % e)
    return self.checker(si)

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

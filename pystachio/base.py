from pprint import pformat

from pystachio.compatibility import Compatibility
from pystachio.naming import (
  Ref,
  Namable)
from pystachio.parsing import MustacheParser
from pystachio.typing import (
  TypeCheck,
  TypeEnvironment)


class Environment(Namable):
  """
    A mount table for Refs pointing to Objects or arbitrary string substitutions.
  """

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
        raise ValueError('Error in Environment.wrap(%s)' % repr(value))

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

  # Duck-typed against provides classmethod.
  #
  # TODO(wickman) provides should probably somehow be integrated with find in this case.
  def provides(self, ref):
    assert isinstance(ref, Ref)
    if ref in self._table:
      return True
    targets = [key for key in self._table if Ref.subscope(key, ref)]
    if not targets:
      return False
    else:
      for key in sorted(targets, reverse=True):
        scope = self._table[key]
        if not isinstance(scope, Namable):
          continue
        subscope = Ref.subscope(key, ref)
        # If subscope is empty, then we should've found it in the ref table.
        assert not subscope.is_empty()
        if scope.provides(subscope):
          return True
    return False

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

  class CoercionError(ValueError):
    def __init__(self, src, dst):
      ValueError.__init__(self, "Cannot coerce '%s' to %s" % (src, dst.__name__))

  class InterpolationError(Exception): pass

  @classmethod
  def checker(cls, obj):
    raise NotImplementedError

  def __init__(self):
    self._scopes = []
    self._modulo = TypeEnvironment()

  def get(self):
    raise NotImplementedError

  def __hash__(self):
    si, _ = self.interpolate()
    return hash(si.get())

  def copy(self):
    """
      Return a copy of this object.
    """
    raise NotImplementedError

  @staticmethod
  def translate_to_scopes(*args, **kw):
    scopes = []
    for arg in args:
      scopes.append(arg if isinstance(arg, Namable) else Environment.wrap(arg))
    scopes.extend([Environment(kw)] if kw else [])
    return scopes

  def bind(self, *args, **kw):
    """
      Bind environment variables into this object's scope.
    """
    new_self = self.copy()
    new_scopes = Object.translate_to_scopes(*args, **kw)
    new_self._scopes = list(reversed(new_scopes)) + new_self._scopes
    return new_self

  def provided(self, environment):
    new_self = self.copy()
    new_self._modulo = new_self._modulo.merge(environment)
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

  def modulo(self):
    return self._modulo

  def check(self):
    """
      Type check this object.
    """
    try:
      si, uninterp = self.interpolate()
    # TODO(wickman) This should probably be pushed out to the interpolate leaves.
    except (Object.CoercionError, MustacheParser.Uninterpolatable) as e:
      return TypeCheck(False, "Unable to interpolate: %s" % e)
    type_environment = self.modulo()
    for ref in uninterp:
      if not type_environment.covers(ref):
        return TypeCheck(False, "Uninterpolated variables: %s" %
          ' '.join('%s' % ref for ref in uninterp))
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

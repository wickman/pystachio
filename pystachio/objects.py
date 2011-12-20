import copy
from collections import Iterable, Mapping
from inspect import isclass

from naming import Namable
from environment import Environment
from parsing import MustacheParser
from schema import Schemaless


class Empty(object):
  """The Empty sentinel representing an unspecified field."""
  pass


class frozendict(dict):
  """A hashable dictionary."""
  def __key(self):
    return tuple((k, self[k]) for k in sorted(self))

  def __hash__(self):
    return hash(self.__key())

  def __eq__(self, other):
    return self.__key() == other.__key()

  def __repr__(self):
    return 'frozendict(%s)' % dict.__repr__(self)


class TypeCheck(object):
  """
    Encapsulate the results of a type check pass.
  """
  class Error(Exception):
    pass

  @staticmethod
  def success():
    return TypeCheck(True, "")

  @staticmethod
  def failure(msg):
    return TypeCheck(False, msg)

  def __init__(self, success, message):
    self._success = success
    self._message = message

  def message(self):
    return self._message

  def ok(self):
    return self._success

  def __repr__(self):
    if self.ok():
      return 'TypeCheck(OK)'
    else:
      return 'TypeCheck(FAILED): %s' % self._message


class ObjectBase(object):
  """
    ObjectBase base class, encapsulating a set of variable bindings scoped to this object.
  """

  class InterpolationError(Exception): pass

  @classmethod
  def checker(cls, obj):
    raise NotImplementedError

  def __init__(self):
    self._scopes = []

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
      if isinstance(arg, Namable):
        scopes.insert(0, arg)
      else:
        scopes.insert(0, Environment.wrap(arg))
    if kw:
      scopes.insert(0, Environment(**kw))
    return scopes

  def bind(self, *args, **kw):
    """
      Bind environment variables into this object's scope.
    """
    new_self = self.copy()
    new_scopes = ObjectBase.translate_to_scopes(*args, **kw)
    new_self._scopes = new_scopes + new_self._scopes
    return new_self

  def in_scope(self, *args, **kw):
    """
      Scope this object to a parent environment (like bind but reversed.)
    """
    new_self = self.copy()
    new_scopes = ObjectBase.translate_to_scopes(*args, **kw)
    new_self._scopes = new_self._scopes + new_scopes
    return new_self

  def scopes(self):
    return self._scopes

  def check(self):
    """
      Type check this object.
    """
    si, _ = self.interpolate()
    return self.checker(si)

  def __ne__(self, other):
    return not (self == other)

  def __mod__(self, namable):
    if isinstance(namable, dict):
      namable = Environment.wrap(namable)
    interp, _ = self.in_scope(namable).interpolate()
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


class Object(ObjectBase):
  """
    A simply-valued (unnamable) object.
  """
  class CoercionError(Exception):
    def __init__(self, src, dst):
      Exception.__init__(self, "Cannot coerce '%s' to %s" % (src, dst.__name__))

  def __init__(self, value):
    self._value = copy.deepcopy(value)
    ObjectBase.__init__(self)

  def get(self):
    return self._value

  def copy(self):
    new_self = self.__class__(self._value)
    new_self._scopes = copy.deepcopy(self.scopes())
    return new_self

  def _my_cmp(self, other):
    if self.__class__ != other.__class__:
      return -1
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    if si._value < oi._value:
      return -1
    elif si._value > oi._value:
      return 1
    else:
      return 0

  def __eq__(self, other):
    return self._my_cmp(other) == 0

  def __lt__(self, other):
    return self._my_cmp(other) == -1

  def __gt__(self, other):
    return self._my_cmp(other) == 1

  def __le__(self, other):
    return self._my_cmp(other) <= 0

  def __ge__(self, other):
    return self._my_cmp(other) >= 0

  def __unicode__(self):
    si, _ = self.interpolate()
    return unicode(si._value)

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, unicode(self))

  def interpolate(self):
    if not isinstance(self._value, basestring):
      return self.__class__(self.coerce(self._value)), []
    else:
      splits = MustacheParser.split(self._value)
      joins, unbound = MustacheParser.join(splits, *self.scopes(), strict=False)
      if unbound:
        return self.__class__(joins), unbound
      else:
        self_copy = self.copy()
        # TODO(wickman) Are these actually the correct semantics?
        if hasattr(self_copy, 'coerce') and callable(self_copy.coerce):
          self_copy._value = self_copy.coerce(joins)
        else:
          self_copy._value = joins
        return self_copy, unbound


class String(Object, Schemaless):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, String):
      return TypeCheck.failure("%s is not a subclass of String" % obj)
    if isinstance(obj._value, basestring):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a string" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = (int, float, basestring)
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise Object.CoercionError(value, cls)
    return unicode(value)

  @classmethod
  def schema_name(cls):
    return 'String'


class Integer(Object, Schemaless):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, Integer):
      return TypeCheck.failure("%s is not a subclass of Integer" % obj)
    if isinstance(obj._value, (int, long)):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not an integer" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = (int, float, basestring)
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise Object.CoercionError(value, cls)
    try:
      return int(value)
    except ValueError:
      raise Object.CoercionError(value, cls)

  @classmethod
  def schema_name(cls):
    return 'Integer'



class Float(Object, Schemaless):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, Float):
      return TypeCheck.failure("%s is not a subclass of Float" % obj)
    if isinstance(obj._value, float):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a float" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = (int, float, basestring)
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise Object.CoercionError(value, cls)
    try:
      return float(value)
    except ValueError:
      raise Object.CoercionError(value, cls)

  @classmethod
  def schema_name(cls):
    return 'Float'

for typ in Integer, String, Float:
  Schemaless.register_schema(typ)

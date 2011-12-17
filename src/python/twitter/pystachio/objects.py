import copy
import types

from collections import Iterable, Mapping
from inspect import isclass
from parsing import (
  Environment,
  MustacheParser)


class Empty(object):
  """The Empty sentinel representing an unspecified field."""
  pass


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
    self._environment = Environment()

  def copy(self):
    """
      Return a copy of this object.
    """
    raise NotImplementedError

  def bind(self, *args, **kw):
    """
      Bind environment variables into this object's scope.
    """
    new_self = self.copy()
    Environment.merge(new_self._environment, Environment(*args, **kw))
    return new_self

  def in_scope(self, *args, **kw):
    """
      Scope this object to a parent environment (like bind but reversed.)
    """
    new_self = self.copy()
    parent_environment = Environment(*args, **kw)
    Environment.merge(parent_environment, new_self._environment)
    new_self._environment = parent_environment
    return new_self

  def environment(self):
    return self._environment

  def check(self):
    """
      Type check this object.
    """
    si, _ = self.interpolate()
    return self.checker(si)

  def __ne__(self, other):
    return not (self == other)

  def __mod__(self, environment):
    def extract_environment(env):
      if isinstance(env, Mapping):
        return env
      elif isinstance(env, ObjectBase):
        return env.environment()
      else:
        raise ValueError("Must interpolate within the context of a mapping or other Object.")
    interp, _ = self.in_scope(extract_environment(environment)).interpolate()
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
    A simply-valued object.
  """
  class CoercionError(Exception):
    def __init__(self, src, dst):
      Exception.__init__(self, "Cannot coerce '%s' to %s" % (src, dst.__name__))

  def __init__(self, value):
    self._value = copy.deepcopy(value)
    ObjectBase.__init__(self)

  def copy(self):
    new_self = self.__class__(self._value)
    new_self._environment = copy.deepcopy(self.environment())
    return new_self

  def __eq__(self, other):
    if self.__class__ != other.__class__:
      return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._value == oi._value

  def __hash__(self):
    si, _ = self.interpolate()
    return hash(si._value)

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (self.__class__.__name__, si._value)

  def interpolate(self):
    if not isinstance(self._value, basestring):
      return self.__class__(self.coerce(self._value)), []
    else:
      splits = MustacheParser.split(self._value)
      joins, unbound = MustacheParser.join(splits, self._environment, strict=False)
      if unbound:
        return self.__class__(joins), unbound
      else:
        self_copy = self.copy()
        if hasattr(self_copy, 'coerce') and callable(self_copy.coerce):
          self_copy._value = self_copy.coerce(joins)
        else:
          self_copy._value = joins
        return self_copy, unbound


class String(Object):
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


class Integer(Object):
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


class Float(Object):
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

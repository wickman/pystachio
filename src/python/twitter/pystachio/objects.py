import copy
import types

from collections import Iterable, Mapping
from inspect import isclass
from parsing import (
  ObjectId,
  ObjectEnvironment,
  ObjectMustacheParser)


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
    self._environment = ObjectEnvironment()

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
    ObjectEnvironment.merge(new_self._environment, ObjectEnvironment(*args, **kw))
    return new_self

  def in_scope(self, *args, **kw):
    """
      Scope this object to a parent environment (like bind but reversed.)
    """
    new_self = self.copy()
    parent_environment = ObjectEnvironment(*args, **kw)
    ObjectEnvironment.merge(parent_environment, new_self._environment)
    new_self._environment = parent_environment
    return new_self

  def environment(self):
    return self._environment

  def check(self):
    """
      Perform post-bind type checking.
    """
    return self.checker(self)

  def interpolate(self):
    """
      Return a copy of this object interpolated in the context of self._environment.
    """
    raise NotImplementedError


class Object(ObjectBase):
  """
    A simply-valued object.
  """
  class CoercionError(Exception):
    def __init__(self, src, dst):
      Exception.__init__(self, "Cannot coerce %s to %s" % (src, dst.__name__))

  def __init__(self, value):
    self._value = copy.deepcopy(value)
    ObjectBase.__init__(self)

  def copy(self):
    new_object = self.__class__(self._value)
    new_object._environment = copy.deepcopy(self._environment)
    return new_object

  def __eq__(self, other):
    if self.__class__ != other.__class__: return False
    si = self.interpolate()
    oi = other.interpolate()
    return si[0]._value == oi[0]._value

  def __ne__(self, other):
    return not (self == other)

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, self._value)

  def interpolate(self):
    if isinstance(self._value, basestring):
      splits = ObjectMustacheParser.split(self._value)
      joins, unbound = ObjectMustacheParser.join(splits, self._environment, strict=False)
      if unbound:
        return self, unbound
      else:
        self_copy = self.copy()
        if hasattr(self_copy, 'coerce') and callable(self_copy.coerce):
          self_copy._value = self_copy.coerce(joins)
        else:
          self_copy._value = joins
        if not self_copy.check().ok():
          raise ObjectBase.InterpolationError(self_copy.check().message())
        else:
          return self_copy, unbound
    else:
      return self, []


class String(Object):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, String):
      return TypeCheck.failure("%s is not a subclass of String" % obj)
    if isinstance(obj._value, str):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a string" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = (int, float, basestring)
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise Object.CoercionError(value, cls)
    return str(value)


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


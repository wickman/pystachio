import copy
import types

from collections import Iterable, Mapping
from inspect import isclass
from parsing import ObjectEnvironment


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
    return self.__class__ == other.__class__ and self._value == other._value

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, self._value)


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



class List(Object):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, List):
      return TypeCheck.failure("%s is not a subclass of List" % obj)
    if isinstance(obj._value, Iterable):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not an iterable" % repr(obj._value))


class Map(Object):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, Map):
      return TypeCheck.failure("%s is not a subclass of Map" % obj)
    if isinstance(obj._value, Mapping):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a mapping" % repr(obj._value))



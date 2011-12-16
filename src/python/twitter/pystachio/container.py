from collections import Iterable
import copy
from inspect import isclass
from objects import (
  Empty,
  ObjectBase,
  Object,
  TypeCheck)

class ListContainer(ObjectBase):
  """
    TODO(wickman):

    Consider what it would tkae for List to take a parameter, e.g.
    List(Integer) or List(String).  As it is, it will be a challenge
    to do interpolation without that type annotation.
  """
  def __init__(self, vals):
    self._values = self._coerce_values(copy.deepcopy(vals))
    ObjectBase.__init__(self)

  def copy(self):
    new_self = self.__class__(self._values)
    new_self._environment = copy.deepcopy(self._environment)
    return new_self

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, ', '.join(map(str, self._values)))

  @staticmethod
  def isiterable(values):
    return isinstance(values, Iterable) and not isinstance(values, basestring)

  def _coerce_values(self, values):
    if not ListContainer.isiterable(values):
      raise ValueError("ListContainer expects an iterable, got %s" % repr(values))
    def coerced(value):
      if isinstance(value, self.TYPE):
        return value
      else:
        return self.TYPE(value)
    return map(coerced, values)

  def check(self):
    if not ListContainer.isiterable(self._values):
      return TypeCheck.failure("ListContainer values are not iterable.")
    for element in self._values:
      if not isinstance(element, self.TYPE):
        raise TypeCheck.failure("Element in %s not of type %s: %s" % (self.__class__.__name__,
          self.TYPE, element))
    return TypeCheck.success()


def List(object_type):
  assert isclass(object_type)
  assert issubclass(object_type, ObjectBase)
  return type.__new__(type, '%sList' % object_type.__name__, (ListContainer,),
    { 'TYPE': object_type })


class MapContainer(ObjectBase):
  """
    TODO(wickman):

    Consider what it would take for Map to take parameters, e.g.
    Map(String, Process)
  """

  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, Map):
      return TypeCheck.failure("%s is not a subclass of Map" % obj)
    if isinstance(obj._value, Mapping):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a mapping" % repr(obj._value))


def Map(key_type, value_type):
  assert isclass(key_type) and isclass(value_type)
  assert issubclass(key_type, ObjectBase) and issubclass(value_type, ObjectBase)
  return type.__new__(type, '%s%sMap' % (key_type.__name__, value_type.__name__), (MapContainer,),
    { 'KEYTYPE': key_type, 'VALUETYPE': value_type })

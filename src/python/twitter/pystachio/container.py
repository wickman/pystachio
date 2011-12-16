from collections import (
  Iterable,
  Mapping)
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
      return TypeCheck.failure("%s values are not iterable." % self.__class__.__name__)
    for element in self._values:
      if not isinstance(element, self.TYPE):
        raise TypeCheck.failure("Element in %s not of type %s: %s" % (self.__class__.__name__,
          self.TYPE.__name__, element))
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
  def __init__(self, input_map):
    self._map = self._coerce_map(copy.deepcopy(input_map))
    ObjectBase.__init__(self)

  def copy(self):
    new_self = self.__class__(self._map)
    new_self._environment = copy.deepcopy(self._environment)
    return new_self

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__,
      ', '.join('%s => %s' % (key, val) for key, val in self._map.items()))

  def _coerce_map(self, input_map):
    if not isinstance(input_map, Mapping):
      raise ValueError("MapContainer expects a Mapping, got %s" % repr(input_map))
    def coerced(key, value):
      coerced_key = key if isinstance(key, self.KEYTYPE) else self.KEYTYPE(key)
      coerced_value = value if isinstance(value, self.VALUETYPE) else self.VALUETYPE(value)
      return (coerced_key, coerced_value)
    return dict(coerced(key, value) for key, value in input_map.items())

  def check(self):
    if not isinstance(self._map, Mapping):
      return TypeCheck.failure("%s map is not a mapping." % self.__class__.__name__)
    for key, value in self._map.items():
      if not isinstance(key, self.KEYTYPE):
        raise TypeCheck.failure("%s key %s is not of type %s" % (self.__class__.__name__,
          key, self.KEYTYPE.__name__))
      if not isinstance(value, self.VALUETYPE):
        raise TypeCheck.failure("%s value %s is not of type %s" % (self.__class__.__name__,
          value, self.VALUETYPE.__name__))
    return TypeCheck.success()


def Map(key_type, value_type):
  assert isclass(key_type) and isclass(value_type)
  assert issubclass(key_type, ObjectBase) and issubclass(value_type, ObjectBase)
  return type.__new__(type, '%s%sMap' % (key_type.__name__, value_type.__name__), (MapContainer,),
    { 'KEYTYPE': key_type, 'VALUETYPE': value_type })

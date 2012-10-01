import copy

from pystachio.base import Object
from pystachio.compatibility import Compatibility
from pystachio.parsing import MustacheParser
from pystachio.typing import Type, TypeFactory, TypeCheck


class SimpleObject(Object, Type):
  """
    A simply-valued (unnamable) object.
  """
  def __init__(self, value):
    self._value = value
    Object.__init__(self)

  def get(self):
    return self._value

  def copy(self):
    new_self = self.__class__(self._value)
    new_self._scopes = copy.copy(self.scopes())
    new_self._modulo = copy.copy(self.modulo())
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

  def __hash__(self):
    return hash(self._value)

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

  def __str__(self):
    si, _ = self.interpolate()
    return str(si._value)

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, str(self) if Compatibility.PY3 else unicode(self))

  def interpolate(self):
    if not isinstance(self._value, Compatibility.stringy):
      return self.__class__(self.coerce(self._value)), []
    else:
      joins, unbound = MustacheParser.resolve(self._value, *self.scopes())
      if unbound:
        return self.__class__(joins), [ref for ref in unbound if not self.modulo().covers(ref)]
      else:
        self_copy = self.copy()
        self_copy._value = self_copy.coerce(joins)
        return self_copy, unbound

  @classmethod
  def type_factory(cls):
    return cls.__name__

  @classmethod
  def type_parameters(cls):
    return ()


class String(SimpleObject):
  @classmethod
  def checker(cls, obj):
    assert isinstance(obj, String)
    if isinstance(obj._value, Compatibility.stringy):
      return TypeCheck.success()
    else:
      # TODO(wickman)  Perhaps we should mark uninterpolated Mustache objects as
      # intrinsically non-stringy, because String will never typecheck false given
      # its input constraints.
      return TypeCheck.failure("%s not a string" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = Compatibility.stringy + Compatibility.numeric
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise cls.CoercionError(value, cls)
    return str(value) if Compatibility.PY3 else unicode(value)


class StringFactory(TypeFactory):
  PROVIDES = 'String'
  @staticmethod
  def create(type_dict, *type_parameters):
    return String


class Integer(SimpleObject):
  @classmethod
  def checker(cls, obj):
    assert isinstance(obj, Integer)
    if isinstance(obj._value, Compatibility.integer):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not an integer" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = Compatibility.numeric + Compatibility.stringy
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise cls.CoercionError(value, cls)
    try:
      return int(value)
    except ValueError:
      raise cls.CoercionError(value, cls)


class IntegerFactory(TypeFactory):
  PROVIDES = 'Integer'
  @staticmethod
  def create(type_dict, *type_parameters):
    return Integer


class Float(SimpleObject):
  @classmethod
  def checker(cls, obj):
    assert isinstance(obj, Float)
    if isinstance(obj._value, Compatibility.real + Compatibility.integer):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a float" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = Compatibility.numeric + Compatibility.stringy
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise cls.CoercionError(value, cls)
    try:
      return float(value)
    except ValueError:
      raise cls.CoercionError(value, cls)

class FloatFactory(TypeFactory):
  PROVIDES = 'Float'
  @staticmethod
  def create(type_dict, *type_parameters):
    return Float

import copy

from pystachio.base import Object, TypeCheck
from pystachio.parsing import MustacheParser
from pystachio.schema import Schemaless

class SimpleObject(Object):
  """
    A simply-valued (unnamable) object.
  """
  class CoercionError(Exception):
    def __init__(self, src, dst):
      Exception.__init__(self, "Cannot coerce '%s' to %s" % (src, dst.__name__))

  def __init__(self, value):
    self._value = copy.deepcopy(value)
    Object.__init__(self)

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


class String(SimpleObject, Schemaless):
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
      raise SimpleObject.CoercionError(value, cls)
    return unicode(value)

  @classmethod
  def schema_name(cls):
    return 'String'


class Integer(SimpleObject, Schemaless):
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
      raise SimpleObject.CoercionError(value, cls)
    try:
      return int(value)
    except ValueError:
      raise SimpleObject.CoercionError(value, cls)

  @classmethod
  def schema_name(cls):
    return 'Integer'



class Float(SimpleObject, Schemaless):
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
      raise SimpleObject.CoercionError(value, cls)
    try:
      return float(value)
    except ValueError:
      raise SimpleObject.CoercionError(value, cls)

  @classmethod
  def schema_name(cls):
    return 'Float'

for typ in Integer, String, Float:
  Schemaless.register_schema(typ)

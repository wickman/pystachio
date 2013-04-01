from .base import Object
from .compatibility import Compatibility
from .naming import Ref
from .parsing import MustacheParser
from .typing import (
    Type,
    TypeCheck,
    TypeFactory,
    TypeMetaclass)


class Fragment(object):
  def __init__(self, fragments):
    for fragment in fragments:
      if not isinstance(fragment, Ref) and not isinstance(fragment, Compatibility.stringy):
        raise ValueError('Unexpected fragment type: %s' % fragment.__class__)
    self._fragments = tuple(fragments)

  @property
  def refs(self):
    return [fragment for fragment in self._fragments if isinstance(fragment, Ref)]

  @property
  def fragments(self):
    return self._fragments

  def __eq__(self, other):
    if self.__class__ != other.__class__:
      return False
    return self._fragments == other._fragments

  def __lt__(self, other):
    return self._fragments < other._fragments

  def __hash__(self):
    return hash(str(self))

  def resolve(self, *namables):
    joins, _ = MustacheParser.join(self._fragments)
    return MustacheParser.resolve(joins, *namables)

  def __str__(self):
    joined, _ = MustacheParser.join(self._fragments)
    return joined

  def __repr__(self):
    return str(self)


class SimpleObject(Object, Type):
  """
    A simply-valued (unnamable) object.
  """
  @classmethod
  def apply(cls, value):
    try:
      value = cls.coerce(value)
    except cls.CoercionError:
      if not isinstance(value, Compatibility.stringy):
        raise
      value = Fragment(MustacheParser.split(value))
      if len(value.refs) == 0:
        raise
    return value

  @classmethod
  def unapply(cls, value):
    if isinstance(value, Fragment):
      joins, _ = value.resolve()
      # TODO(wickman) Perhaps unapply should take a strict bit?
      # return cls.coerce(joins)
      return joins
    return value

  def _my_cmp(self, other):
    if self.__class__ != other.__class__:
      return -1
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    if si._value.__class__ != oi._value.__class__:
      return -1
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
    if not isinstance(self._value, Fragment):
      # TODO(wickman) Do we need to return a copy?
      return self.copy(), []
    joins, unbound = self._value.resolve(*self.scopes())
    return self.__class__(joins), unbound

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
    if isinstance(value, Compatibility.stringy) and any(
        isinstance(ref, Ref) for ref in MustacheParser.split(value)):
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


class Boolean(SimpleObject):
  @classmethod
  def checker(cls, obj):
    assert isinstance(obj, Boolean)
    if isinstance(obj._value, bool):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a boolean" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = (bool,) + Compatibility.numeric + Compatibility.stringy
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise cls.CoercionError(value, cls)

    if isinstance(value, bool):
      return value
    elif isinstance(value, Compatibility.stringy):
      if value.lower() in ("true", "1"):
        return True
      elif value.lower() in ("false", "0"):
        return False
      else:
        raise cls.CoercionError(value, cls)
    else:
      return bool(value)

class BooleanFactory(TypeFactory):
  PROVIDES = 'Boolean'
  @staticmethod
  def create(type_dict, *type_parameters):
    return Boolean


class EnumContainer(SimpleObject):
  @classmethod
  def checker(cls, obj):
    assert isinstance(obj, EnumContainer)
    if isinstance(obj._value, Compatibility.stringy) and obj._value in cls.VALUES:
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not in the enumeration (%s)" % (repr(obj._value),
        ', '.join(cls.VALUES)))

  @classmethod
  def coerce(cls, value):
    if not isinstance(value, Compatibility.stringy) or value not in cls.VALUES:
      raise cls.CoercionError(value, cls, '%s is not one of %s' % (
        value, ', '.join(cls.VALUES)))
    return str(value) if Compatibility.PY3 else unicode(value)

  @classmethod
  def type_factory(cls):
    return 'Enum'

  @classmethod
  def type_parameters(cls):
    return (cls.__name__, cls.VALUES)

class EnumFactory(TypeFactory):
  PROVIDES = 'Enum'

  @staticmethod
  def create(type_dict, *type_parameters):
    """
      EnumFactory.create(*type_parameters) expects:
        enumeration name, (enumeration values)
    """
    name, values = type_parameters
    assert isinstance(values, (list, tuple))
    for value in values:
      assert isinstance(value, Compatibility.stringy)
    return TypeMetaclass(str(name), (EnumContainer,), { 'VALUES': values })

def Enum(*stuff):
  # TODO(wickman) Check input
  if len(stuff) == 2 and isinstance(stuff[0], Compatibility.stringy) and isinstance(stuff[1], (list, tuple)):
    name, values = stuff
    return TypeFactory.new({}, EnumFactory.PROVIDES, name, values)
  else:
    return TypeFactory.new({}, EnumFactory.PROVIDES, 'Enum_' + '_'.join(stuff), stuff)

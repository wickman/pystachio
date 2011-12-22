from collections import Iterable, Mapping
import copy
from inspect import isclass

from pystachio.base import Object, TypeCheck, frozendict
from pystachio.naming import Namable
from pystachio.schema import Schema

class ListContainer(Object, Schema, Namable):
  """
    The List container type.  This is the base class for all user-generated
    List types.  It won't function as-is, since it requires cls.TYPE to be
    set to the contained type.  If you want a concrete List type, see the
    List() function.
  """
  _MEMOIZED_TYPES = {}

  @staticmethod
  def new(klazz):
    """
      Construct a List containing type 'klazz'.
    """
    assert isclass(klazz)
    assert issubclass(klazz, Object)
    if klazz not in ListContainer._MEMOIZED_TYPES:
      ListContainer._MEMOIZED_TYPES[klazz] = type('%sList' % klazz.__name__,
        (ListContainer,), { 'TYPE': klazz })
    return ListContainer._MEMOIZED_TYPES[klazz]

  def __init__(self, vals):
    self._values = self._coerce_values(copy.deepcopy(vals))
    Object.__init__(self)

  def get(self):
    return [v.get() for v in self._values]

  def copy(self):
    new_self = self.__class__(self._values)
    new_self._scopes = copy.deepcopy(self.scopes())
    return new_self

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (self.__class__.__name__, ', '.join(map(unicode, si._values)))

  def __eq__(self, other):
    if not isinstance(other, ListContainer): return False
    if self.TYPE != other.TYPE: return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._values == oi._values

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
        return TypeCheck.failure("Element in %s not of type %s: %s" % (self.__class__.__name__,
          self.TYPE.__name__, element))
      else:
        if not element.check().ok():
          return TypeCheck.failure("Element in %s failed check: %s" % (self.__class__.__name__,
            element.check().message()))
    return TypeCheck.success()

  def interpolate(self):
    unbound = set()
    interpolated = []
    for element in self._values:
      einterp, eunbound = element.in_scope(*self.scopes()).interpolate()
      interpolated.append(einterp)
      unbound.update(eunbound)
    return self.__class__(interpolated), list(unbound)

  def find(self, ref):
    if not ref.is_index():
      raise Namable.NamingError(self, ref)
    try:
      intvalue = int(ref.action().value)
    except ValueError:
      raise Namable.NotFound(self, ref)
    if len(self._values) <= intvalue:
      raise Namable.NotFound(self, ref)
    else:
      namable = self._values[intvalue]
      if ref.rest().is_empty():
        return namable.in_scope(*self.scopes())
      else:
        if not isinstance(namable, Namable):
          raise Namable.Unnamable(namable)
        else:
          return namable.in_scope(*self.scopes()).find(ref.rest())

  @classmethod
  def schema_name(cls):
    return 'ListContainer'

  @classmethod
  def serialize_schema(cls):
    return (cls.schema_name(), {
      '__name__': cls.__name__,
      '__containing__': cls.TYPE.serialize_schema()
    })

  @staticmethod
  def deserialize_schema(schema):
    _, schema_parameters = schema
    contained_type = Schema.deserialize_schema(schema_parameters['__containing__'])
    real_type = ListContainer.new(contained_type)
    assert schema_parameters['__name__'] == real_type.__name__
    return real_type

Schema.register_schema(ListContainer)
List = ListContainer.new


class MapContainer(Object, Schema, Namable):
  """
    The Map container type.  This is the base class for all user-generated
    Map types.  It won't function as-is, since it requires cls.KEYTYPE and
    cls.VALUETYPE to be set to the appropriate types.  If you want a
    concrete Map type, see the Map() function.
  """
  _MEMOIZED_TYPES = {}

  @staticmethod
  def new(key_cls, value_cls):
    assert isclass(key_cls) and isclass(value_cls)
    assert issubclass(key_cls, Object) and issubclass(value_cls, Object)
    if (key_cls, value_cls) not in MapContainer._MEMOIZED_TYPES:
      MapContainer._MEMOIZED_TYPES[(key_cls, value_cls)] = type(
        '%s%sMap' % (key_cls.__name__, value_cls.__name__), (MapContainer,),
        { 'KEYTYPE': key_cls, 'VALUETYPE': value_cls })
    return MapContainer._MEMOIZED_TYPES[(key_cls, value_cls)]

  def __init__(self, input_map):
    self._map = self._coerce_map(copy.deepcopy(input_map))
    Object.__init__(self)

  def get(self):
    return frozendict((k.get(), v.get()) for (k, v) in self._map.items())

  def copy(self):
    new_self = self.__class__(self._map)
    new_self._scopes = copy.deepcopy(self.scopes())
    return new_self

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (self.__class__.__name__,
      ', '.join('%s => %s' % (key, val) for key, val in si._map.items()))

  def __eq__(self, other):
    if not isinstance(other, MapContainer): return False
    if self.KEYTYPE != other.KEYTYPE: return False
    if self.VALUETYPE != other.VALUETYPE: return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._map == oi._map

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
        return TypeCheck.failure("%s key %s is not of type %s" % (self.__class__.__name__,
          key, self.KEYTYPE.__name__))
      if not isinstance(value, self.VALUETYPE):
        return TypeCheck.failure("%s value %s is not of type %s" % (self.__class__.__name__,
          value, self.VALUETYPE.__name__))
      if not key.check().ok():
        return TypeCheck.failure("%s key %s failed check: %s" % (self.__class__.__name__,
          key, key.check().message()))
      if not value.check().ok():
        return TypeCheck.failure("%s[%s] value %s failed check: %s" % (self.__class__.__name__,
          key, value, value.check().message()))
    return TypeCheck.success()

  def interpolate(self):
    unbound = set()
    interpolated = {}
    for key, value in self._map.items():
      kinterp, kunbound = key.in_scope(*self.scopes()).interpolate()
      vinterp, vunbound = value.in_scope(*self.scopes()).interpolate()
      unbound.update(kunbound)
      unbound.update(vunbound)
      interpolated[kinterp] = vinterp
    return self.__class__(interpolated), list(unbound)

  def find(self, ref):
    if not ref.is_index():
      raise Namable.NamingError(self, ref)
    kvalue = self.KEYTYPE(ref.action().value)
    if kvalue not in self._map:
      raise Namable.NotFound(self, ref)
    else:
      namable = self._map[kvalue]
      if ref.rest().is_empty():
        return namable.in_scope(*self.scopes())
      else:
        if not isinstance(namable, Namable):
          raise Namable.Unnamable(namable)
        else:
          return namable.in_scope(*self.scopes()).find(ref.rest())

  @classmethod
  def schema_name(cls):
    return 'MapContainer'

  @classmethod
  def serialize_schema(cls):
    return (cls.schema_name(), {
      '__name__': cls.__name__,
      '__keys__': cls.KEYTYPE.serialize_schema(),
      '__values__': cls.VALUETYPE.serialize_schema()
    })

  @staticmethod
  def deserialize_schema(schema):
    _, schema_parameters = schema
    key_type = Schema.deserialize_schema(schema_parameters['__keys__'])
    value_type = Schema.deserialize_schema(schema_parameters['__values__'])
    real_type = MapContainer.new(key_type, value_type)
    assert schema_parameters['__name__'] == real_type.__name__
    return real_type

Schema.register_schema(MapContainer)
Map = MapContainer.new

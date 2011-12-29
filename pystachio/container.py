from collections import Iterable, Mapping
import copy
from inspect import isclass

from pystachio import Types
from pystachio.base import Object, frozendict
from pystachio.naming import Namable
from pystachio.typing import TypeFactory, Type, TypeCheck, TypeMetaclass

class ListFactory(TypeFactory):
  PROVIDES = 'List'

  @staticmethod
  def create(type_dict, *type_parameters):
    """
      Construct a List containing type 'klazz'.
    """
    assert len(type_parameters) == 1
    klazz = TypeFactory.new(type_dict, *type_parameters[0])
    assert isclass(klazz)
    assert issubclass(klazz, Object)
    return TypeMetaclass('%sList' % klazz.__name__, (ListContainer,), { 'TYPE': klazz })


class ListContainer(Namable, Object, Type):
  """
    The List container type.  This is the base class for all user-generated
    List types.  It won't function as-is, since it requires cls.TYPE to be
    set to the contained type.  If you want a concrete List type, see the
    List() function.
  """
  def __init__(self, vals):
    self._values = self._coerce_values(copy.copy(vals))
    Object.__init__(self)

  def get(self):
    return tuple([v.get() for v in self._values])

  def copy(self):
    new_self = self.__class__(self._values)
    new_self._scopes = copy.copy(self.scopes())
    return new_self

  def __hash__(self):
    return hash(self.get())

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (self.__class__.__name__,
      ', '.join(str(v) if Types.PY3 else unicode(v) for v in si._values))

  def __eq__(self, other):
    if not isinstance(other, ListContainer): return False
    if self.TYPE.serialize_type() != other.TYPE.serialize_type(): return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._values == oi._values

  @staticmethod
  def isiterable(values):
    return isinstance(values, Iterable) and not isinstance(values, Types.stringy)

  def _coerce_values(self, values):
    if not ListContainer.isiterable(values):
      raise ValueError("ListContainer expects an iterable, got %s" % repr(values))
    def coerced(value):
      return value if isinstance(value, self.TYPE) else self.TYPE(value)
    return tuple([coerced(v) for v in values])

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
  def type_factory(cls):
    return 'List'

  @classmethod
  def type_parameters(cls):
    return (cls.TYPE.serialize_type(),)

List = TypeFactory.wrapper(ListFactory)


class MapFactory(TypeFactory):
  PROVIDES = 'Map'

  @staticmethod
  def create(type_dict, *type_parameters):
    assert len(type_parameters) == 2, 'Type parameters: %s' % repr(type_parameters)
    key_klazz, value_klazz = type_parameters
    key_klazz, value_klazz = (TypeFactory.new(type_dict, *key_klazz),
                              TypeFactory.new(type_dict, *value_klazz))
    assert isclass(key_klazz) and isclass(value_klazz)
    assert issubclass(key_klazz, Object) and issubclass(value_klazz, Object)
    return TypeMetaclass('%s%sMap' % (key_klazz.__name__, value_klazz.__name__), (MapContainer,),
      { 'KEYTYPE': key_klazz, 'VALUETYPE': value_klazz })


class MapContainer(Namable, Object, Type):
  """
    The Map container type.  This is the base class for all user-generated
    Map types.  It won't function as-is, since it requires cls.KEYTYPE and
    cls.VALUETYPE to be set to the appropriate types.  If you want a
    concrete Map type, see the Map() function.

    __init__(dict) => translates to list of tuples & sanity checks
    __init__(tuple) => sanity checks
  """
  def __init__(self, *args):
    """
      Construct a map.

      Input:
        sequence of tuples _or_ a dictionary
    """
    if len(args) == 1 and isinstance(args[0], Mapping):
      self._map = self._coerce_map(copy.copy(args[0]))
    elif all(isinstance(arg, Iterable) and len(arg)==2 for arg in args):
      self._map = self._coerce_tuple(args)
    else:
      raise ValueError("Unexpected input to MapContainer: %s" % repr(args))
    Object.__init__(self)

  def get(self):
    return frozendict((k.get(), v.get()) for (k, v) in self._map)

  def _coerce_wrapper(self, key, value):
    coerced_key = key if isinstance(key, self.KEYTYPE) else self.KEYTYPE(key)
    coerced_value = value if isinstance(value, self.VALUETYPE) else self.VALUETYPE(value)
    return (coerced_key, coerced_value)

  def _coerce_map(self, input_map):
    return tuple(self._coerce_wrapper(key, value) for key, value in input_map.items())

  def _coerce_tuple(self, input_tuple):
    return tuple(self._coerce_wrapper(key, value) for key, value in input_tuple)

  def __hash__(self):
    return hash(self.get())

  def copy(self):
    new_self = self.__class__(*self._map)
    new_self._scopes = copy.copy(self.scopes())
    return new_self

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (self.__class__.__name__,
      ', '.join('%s => %s' % (key, val) for key, val in si._map))

  def __eq__(self, other):
    if not isinstance(other, MapContainer): return False
    if self.KEYTYPE.serialize_type() != other.KEYTYPE.serialize_type(): return False
    if self.VALUETYPE.serialize_type() != other.VALUETYPE.serialize_type(): return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._map == oi._map

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
    interpolated = []
    for key, value in self._map:
      kinterp, kunbound = key.in_scope(*self.scopes()).interpolate()
      vinterp, vunbound = value.in_scope(*self.scopes()).interpolate()
      unbound.update(kunbound)
      unbound.update(vunbound)
      interpolated.append((kinterp, vinterp))
    return self.__class__(*interpolated), list(unbound)

  def find(self, ref):
    if not ref.is_index():
      raise Namable.NamingError(self, ref)
    kvalue = self.KEYTYPE(ref.action().value)
    for key, namable in self._map:
      if kvalue == key:
        if ref.rest().is_empty():
          return namable.in_scope(*self.scopes())
        else:
          if not isinstance(namable, Namable):
            raise Namable.Unnamable(namable)
          else:
            return namable.in_scope(*self.scopes()).find(ref.rest())
    raise Namable.NotFound(self, ref)

  @classmethod
  def type_factory(cls):
    return 'Map'

  @classmethod
  def type_parameters(cls):
    return (cls.KEYTYPE.serialize_type(), cls.VALUETYPE.serialize_type())


Map = TypeFactory.wrapper(MapFactory)

from collections import Iterable, Mapping, Sequence
import copy
from inspect import isclass

from .base import Object
from .compatibility import Compatibility
from .naming import Namable, Ref, frozendict
from .typing import (
    Type,
    TypeFactory,
    TypeMetaclass)


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
    return TypeMetaclass('%sList' % klazz.__name__, (ListContainer,), {'TYPE': klazz})


class ListContainer(Object, Namable, Type):
  """
    The List container type.  This is the base class for all user-generated
    List types.  It won't function as-is, since it requires cls.TYPE to be
    set to the contained type.  If you want a concrete List type, see the
    List() function.
  """
  @classmethod
  def isiterable(cls, values):
    return isinstance(values, Sequence) and not isinstance(values, Compatibility.stringy)

  @classmethod
  def init(cls, values):
    if not cls.isiterable(values):
      raise ValueError("ListContainer expects an iterable, got %s" % repr(values))
    def coerced(value):
      return value if isinstance(value, cls.TYPE) else cls.TYPE(value)
    return tuple(coerced(v) for v in values)

  def __hash__(self):
    return hash(self.get())

  def __iter__(self):
    for v in self._value:
      yield v.bind(*self.scopes())

  def __getitem__(self, index_or_slice):
    return self._value[index_or_slice].bind(*self.scopes())

  def __contains__(self, item):
    si, _ = self.interpolate()
    return (item.get() if isinstance(item, self.TYPE) else item) in si

  def __eq__(self, other):
    if not isinstance(other, ListContainer):
      return False
    if self.TYPE.serialize_type() != other.TYPE.serialize_type():
      return False
    si, si_refs = self.interpolate()
    oi, oi_refs = other.interpolate()
    return si == oi and si_refs == oi_refs

  def interpolate(self):
    unbound = set()
    interpolated = []
    for element in self._value:
      einterp, eunbound = element.in_scope(*self.scopes()).interpolate()
      interpolated.append(einterp)
      unbound.update(eunbound)
    return tuple(interpolated), list(unbound)

  def find(self, ref):
    if not ref.is_index():
      raise Namable.NamingError(self, ref)
    try:
      intvalue = int(ref.action().value)
    except ValueError:
      raise Namable.NamingError(self, ref)
    if len(self._value) <= intvalue:
      raise Namable.NotFound(self, ref)
    else:
      namable = self._value[intvalue]
      if ref.rest().is_empty():
        return namable.in_scope(*self.scopes())
      else:
        if not isinstance(namable, Namable):
          raise Namable.Unnamable(namable)
        else:
          return namable.in_scope(*self.scopes()).find(ref.rest())

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__,
        ', '.join(map(Compatibility.to_str, self)))

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
      {'KEYTYPE': key_klazz, 'VALUETYPE': value_klazz})


# TODO(wickman) Technically it's possible to do the following:
#
# >>> my_map = Map(Boolean,Integer)((True,2), (False,3), (False, 2))
# >>> my_map
# BooleanIntegerMap(True => 2, False => 3, False => 2)
# >>> my_map.get()
# frozendict({False: 2, True: 2})
# >>> my_map[True]
# Integer(2)
# >>> my_map.get()[True]
# 2
# we should filter tuples for uniqueness.
class MapContainer(Object, Namable, Type):
  """
    The Map container type.  This is the base class for all user-generated
    Map types.  It won't function as-is, since it requires cls.KEYTYPE and
    cls.VALUETYPE to be set to the appropriate types.  If you want a
    concrete Map type, see the Map() function.

    __init__(dict) => translates to list of tuples & sanity checks
    __init__(tuple) => sanity checks
  """
  @classmethod
  def init(cls, *args):
    if len(args) == 1 and isinstance(args[0], Mapping):
      return cls.coerce_map(copy.copy(args[0]))
    elif all(isinstance(arg, Iterable) and len(arg) == 2 for arg in args):
      return cls.coerce_tuple(args)
    else:
      raise ValueError("Unexpected input to MapContainer: %s" % repr(args))

  @classmethod
  def coerce_wrapper(cls, key, value):
    coerced_key = key if isinstance(key, cls.KEYTYPE) else cls.KEYTYPE(key)
    coerced_value = value if isinstance(value, cls.VALUETYPE) else cls.VALUETYPE(value)
    return (coerced_key, coerced_value)

  @classmethod
  def coerce_map(cls, input_map):
    return tuple(cls.coerce_wrapper(key, value) for key, value in input_map.items())

  @classmethod
  def coerce_tuple(cls, input_tuple):
    return tuple(cls.coerce_wrapper(key, value) for key, value in input_tuple)

  @classmethod
  def coerce(cls, tuple_list):
    return frozendict(tuple_list)

  def __hash__(self):
    return hash(self.get())

  def __iter__(self):
    for key, _ in self._value:
      yield key.bind(*self.scopes())

  def __getitem__(self, key):
    if not isinstance(key, self.KEYTYPE):
      try:
        key = self.KEYTYPE(key)
      except ValueError:
        raise KeyError("%s is not coercable to %s" % self.KEYTYPE.__name__)
    si, _ = self.interpolate()
    for k, v in si:
      if key == k:
        return v
    raise KeyError("%s not found" % key)

  def __contains__(self, item):
    try:
      self[item]
      return True
    except KeyError:
      return False

  def __eq__(self, other):
    if not isinstance(other, MapContainer):
      return False
    if self.KEYTYPE.serialize_type() != other.KEYTYPE.serialize_type():
      return False
    if self.VALUETYPE.serialize_type() != other.VALUETYPE.serialize_type():
      return False
    si, si_refs = self.interpolate()
    oi, oi_refs = other.interpolate()
    return si == oi and si_refs == oi_refs

  def interpolate(self):
    unbound = set()
    interpolated = []
    for key, value in self._value:
      kinterp, kunbound = key.in_scope(*self.scopes()).interpolate()
      vinterp, vunbound = value.in_scope(*self.scopes()).interpolate()
      unbound.update(kunbound)
      unbound.update(vunbound)
      interpolated.append((kinterp, vinterp))
    return self.coerce(interpolated), list(unbound)

  def find(self, ref):
    if not ref.is_index():
      raise Namable.NamingError(self, ref)
    kvalue = self.KEYTYPE(ref.action().value)
    for key, namable in self._value:
      if kvalue == key:
        if ref.rest().is_empty():
          return namable.in_scope(*self.scopes())
        else:
          if not isinstance(namable, Namable):
            raise Namable.Unnamable(namable)
          else:
            return namable.in_scope(*self.scopes()).find(ref.rest())
    raise Namable.NotFound(self, ref)

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__,
      ', '.join('%s => %s' % (key.bind(*self.scopes()), val.bind(*self.scopes()))
           for key, val in self._value))

  @classmethod
  def type_factory(cls):
    return 'Map'

  @classmethod
  def type_parameters(cls):
    return (cls.KEYTYPE.serialize_type(), cls.VALUETYPE.serialize_type())


Map = TypeFactory.wrapper(MapFactory)

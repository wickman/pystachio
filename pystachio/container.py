from collections import Iterable, Mapping, Sequence
import copy
from inspect import isclass

from .base import Object
from .compatibility import Compatibility
from .naming import Namable, Ref, frozendict
from .typing import (
    Type,
    TypeCheck,
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
    return TypeMetaclass('%sList' % klazz.__name__, (ListContainer,), { 'TYPE': klazz })


class ListContainer(Object, Namable, Type):
  """
    The List container type.  This is the base class for all user-generated
    List types.  It won't function as-is, since it requires cls.TYPE to be
    set to the contained type.  If you want a concrete List type, see the
    List() function.
  """
  __slots__ = ('_value',)

  @classmethod
  def _coerce_values(cls, values):
    if not ListContainer.isiterable(values):
      raise ValueError("ListContainer expects an iterable, got %s" % repr(values))
    def coerced(value):
      return value if isinstance(value, cls.TYPE) else cls.TYPE(value)
    return tuple([coerced(v) for v in values])

  @classmethod
  def apply(cls, values):
    return cls._coerce_values(copy.copy(values))

  @classmethod
  def unapply(cls, value):
    return tuple(v.get() for v in value)

  def __hash__(self):
    return hash(self.get())

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (self.__class__.__name__,
      ', '.join(str(v) if Compatibility.PY3 else unicode(v) for v in si._value))

  def __iter__(self):
    si, _ = self.interpolate()
    return iter(si._value)

  def __getitem__(self, index_or_slice):
    si, _ = self.interpolate()
    return si._value[index_or_slice]

  def __contains__(self, item):
    si, _ = self.interpolate()
    if isinstance(item, self.TYPE):
      return item in si._value
    else:
      return item in si.get()

  def __eq__(self, other):
    if not isinstance(other, ListContainer): return False
    if self.TYPE.serialize_type() != other.TYPE.serialize_type(): return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._value == oi._value

  @staticmethod
  def isiterable(values):
    return isinstance(values, Sequence) and not isinstance(values, Compatibility.stringy)



  def check(self):
    assert ListContainer.isiterable(self._value)
    for element in self._value:
      assert isinstance(element, self.TYPE)
      typecheck = element.in_scope(*self.scopes()).check()
      if not typecheck.ok():
        return TypeCheck.failure("Element in %s failed check: %s" % (self.__class__.__name__,
          typecheck.message()))
    return TypeCheck.success()

  def interpolate(self):
    unbound = set()
    interpolated = []
    for element in self._value:
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
  __slots__ = ('_value',)

  @classmethod
  def _coerce_wrapper(cls, key, value):
    coerced_key = key if isinstance(key, cls.KEYTYPE) else cls.KEYTYPE(key)
    coerced_value = value if isinstance(value, cls.VALUETYPE) else cls.VALUETYPE(value)
    return (coerced_key, coerced_value)

  @classmethod
  def _coerce_map(cls, input_map):
    return tuple(cls._coerce_wrapper(key, value) for key, value in input_map.items())

  @classmethod
  def _coerce_tuple(cls, input_tuple):
    return tuple(cls._coerce_wrapper(key, value) for key, value in input_tuple)

  @classmethod
  def apply(cls, *args):
    if len(args) == 1 and isinstance(args[0], Mapping):
      value = cls._coerce_map(copy.copy(args[0]))
    elif all(isinstance(arg, Iterable) and len(arg) == 2 for arg in args):
      value = cls._coerce_tuple(args)
    else:
      raise ValueError("Unexpected input to MapContainer: %s" % repr(args))
    return value
  
  @classmethod
  def unapply(cls, value):
    return frozendict((k.get(), v.get()) for (k, v) in value)

  def __hash__(self):
    return hash(self.get())

  def __iter__(self):
    si, _ = self.interpolate()
    return (t[0] for t in si._value)

  def __getitem__(self, key):
    if not isinstance(key, self.KEYTYPE):
      try:
        key = self.KEYTYPE(key)
      except ValueError:
        raise KeyError
    # TODO(wickman) The performance of this should be improved.
    si, _ = self.interpolate()
    for tup in si._value:
      if key == tup[0]:
        return tup[1]
    raise KeyError("%s not found" % key)

  def __contains__(self, item):
    try:
      self[item]
      return True
    except KeyError:
      return False

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (self.__class__.__name__,
      ', '.join('%s => %s' % (key, val) for key, val in si._value))

  def __eq__(self, other):
    if not isinstance(other, MapContainer): return False
    if self.KEYTYPE.serialize_type() != other.KEYTYPE.serialize_type(): return False
    if self.VALUETYPE.serialize_type() != other.VALUETYPE.serialize_type(): return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._value == oi._value

  def check(self):
    assert isinstance(self._value, tuple)
    for key, value in self._value:
      assert isinstance(key, self.KEYTYPE)
      assert isinstance(value, self.VALUETYPE)
      keycheck = key.in_scope(*self.scopes()).check()
      valuecheck = value.in_scope(*self.scopes()).check()
      if not keycheck.ok():
        return TypeCheck.failure("%s key %s failed check: %s" % (self.__class__.__name__,
          key, keycheck.message()))
      if not valuecheck.ok():
        return TypeCheck.failure("%s[%s] value %s failed check: %s" % (self.__class__.__name__,
          key, value, valuecheck.message()))
    return TypeCheck.success()

  def interpolate(self):
    unbound = set()
    interpolated = []
    for key, value in self._value:
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

  @classmethod
  def type_factory(cls):
    return 'Map'

  @classmethod
  def type_parameters(cls):
    return (cls.KEYTYPE.serialize_type(), cls.VALUETYPE.serialize_type())


Map = TypeFactory.wrapper(MapFactory)

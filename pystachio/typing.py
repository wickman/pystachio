import functools
from inspect import isclass

from pystachio.naming import Ref, Namable, frozendict


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


class TypeFactoryType(type):
  _TYPE_FACTORIES = {}

  def __new__(mcs, name, parents, attributes):
    if 'PROVIDES' not in attributes:
      return type.__new__(mcs, name, parents, attributes)
    else:
      provides = attributes['PROVIDES']
      new_type = type.__new__(mcs, name, parents, attributes)
      TypeFactoryType._TYPE_FACTORIES[provides] = new_type
      return new_type


TypeFactoryClass = TypeFactoryType('TypeFactoryClass', (object,), {})
class TypeFactory(TypeFactoryClass):
  @staticmethod
  def get_factory(type_name):
    assert type_name in TypeFactoryType._TYPE_FACTORIES, (
      'Unknown type: %s, Existing factories: %s' % (
        type_name, TypeFactoryType._TYPE_FACTORIES.keys()))
    return TypeFactoryType._TYPE_FACTORIES[type_name]

  @staticmethod
  def create(type_dict, *type_parameters):
    """
      Implemented by the TypeFactory to produce a new type.

      Should return:
        reified type
        (with usable type.__name__)
    """
    raise NotImplementedError("create unimplemented for: %s" % repr(type_parameters))

  @staticmethod
  def new(type_dict, type_factory, *type_parameters):
    """
      Create a fully reified type from a type schema.
    """
    type_tuple = (type_factory,) + type_parameters
    if type_tuple not in type_dict:
      factory = TypeFactory.get_factory(type_factory)
      reified_type = factory.create(type_dict, *type_parameters)
      type_dict[type_tuple] = reified_type
    return type_dict[type_tuple]

  @staticmethod
  def wrapper(factory):
    assert issubclass(factory, TypeFactory)
    def wrapper_function(*type_parameters):
      return TypeFactory.new({}, factory.PROVIDES, *tuple(
        [typ.serialize_type() for typ in type_parameters]))
    return wrapper_function

  @staticmethod
  def load(type_tuple, into=None):
    """
      Determine all types touched by loading the type and deposit them into
      the particular namespace.
    """
    type_dict = {}
    TypeFactory.new(type_dict, *type_tuple)
    deposit = into if (into is not None and isinstance(into, dict)) else {}
    for reified_type in type_dict.values():
      deposit[reified_type.__name__] = reified_type
    return deposit

  @staticmethod
  def load_json(json_list, into=None):
    """
      Determine all types touched by loading the type and deposit them into
      the particular namespace.
    """
    def l2t(obj):
      if isinstance(obj, list):
        return tuple(l2t(L) for L in obj)
      elif isinstance(obj, dict):
        return frozendict(obj)
      else:
        return obj
    return TypeFactory.load(l2t(json_list), into=into)

  @staticmethod
  def load_file(filename, into=None):
    import json
    with open(filename) as fp:
      return TypeFactory.load_json(json.load(fp), into=into)


class TypeMetaclass(type):
  def __instancecheck__(cls, other):
    if not hasattr(other, 'type_parameters'):
      return False
    if not hasattr(other, '__class__'):
      return False
    if cls.__name__ != other.__class__.__name__:
      return False
    return cls.type_factory() == other.type_factory() and (
      cls.type_parameters() == other.type_parameters())

  def __new__(mcls, name, parents, attributes):
    return type.__new__(mcls, name, parents, attributes)


class Type(object):
  @classmethod
  def type_factory(cls):
    """ Return the name of the factory that produced this class. """
    raise NotImplementedError

  @classmethod
  def type_parameters(cls):
    """ Return the type parameters used to produce this class. """
    raise NotImplementedError

  @classmethod
  def serialize_type(cls):
    return (cls.type_factory(),) + cls.type_parameters()

  @classmethod
  def dump(cls, fp):
    import json
    json.dump(cls.serialize_type(), fp)

  def check(self):
    """
      Returns a TypeCheck object explaining whether or not a particular
      instance of this object typechecks.
    """
    raise NotImplementedError


class TypeEnvironment(object):
  @staticmethod
  def deserialize(klazz_bindings, type_dict):
    unbound_types = []
    bound_types = {}

    for binding in klazz_bindings:
      if len(binding) == 1:
        unbound_types.append(TypeFactory.new(type_dict, *binding[0]))
      elif len(binding) == 2:
        bound_types[binding[1]] = TypeFactory.new(type_dict, *binding[0])
      else:
        raise ValueError('Expected 1- or 2-tuple to TypeEnvironment.deserialize')

    return TypeEnvironment(*unbound_types, **bound_types)

  def __init__(self, *types, **bound_types):
    for typ in types + tuple(bound_types.values()):
      if not isclass(typ) or not issubclass(typ, Namable):
        raise TypeError('Type annotations must be subtypes of Namable, got %s instead!' % repr(typ))
    self._unbound_types = types
    self._bound_types = bound_types

  def merge(self, other):
    self_serialized = self.serialize()
    other_serialized = other.serialize()
    combined = set(self_serialized + other_serialized)
    return TypeEnvironment.deserialize(tuple(combined), {})

  def serialize(self):
    serialized_bindings = []
    for typ in self._unbound_types:
      serialized_bindings.append((typ.serialize_type(),))
    for (name, typ) in self._bound_types.items():
      serialized_bindings.append((typ.serialize_type(), name))
    return tuple(serialized_bindings)

  def covers(self, ref):
    """
      Does this TypeEnvironment cover the ref?
    """
    for binding in self._unbound_types:
      if binding.provides(ref):
        return True
    for bound_name, binding in self._bound_types.items():
      scoped_ref = Ref.from_address(bound_name).scoped_to(ref)
      if scoped_ref is not None and binding.provides(scoped_ref):
        return True
    return False

  def __str__(self):
    return 'TypeEnvironment(%s, %s)' % (
      ' '.join(unbound.__name__ for unbound in self._unbound_types),
      ' '.join('%s=>%s' % (name, bound.__name__) for name, bound in self._bound_types.items()))

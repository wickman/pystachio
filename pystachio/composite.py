import copy
import json
from collections import Mapping
from inspect import isclass

from .base import Environment, Object
from .naming import Namable, frozendict
from .typing import Type, TypeCheck, TypeFactory, TypeMetaclass


class Empty(object):
  """The Empty sentinel representing an unspecified field."""
  pass


class TypeSignature(object):
  """
    Type metadata for composite type schemas.
  """

  def __init__(self, cls, required=False, default=Empty):
    """Create an instance of a type signature.
    Args:
        cls (Class): the "type" of the object this signature represents.
        required (bool):
        default(object): an instance of the type for a default value. This
           should be either an instance of cls or something coercable to cls.
    """
    assert isclass(cls)
    assert issubclass(cls, Object)
    if default is not Empty and not isinstance(default, cls):
      self._default = cls(default)
    else:
      self._default = default
    self._cls = cls
    self._required = required

  def serialize(self):
    return (self.required,
            self.default.get() if not self.empty else (),
            self.empty,
            self.klazz.serialize_type())

  @staticmethod
  def deserialize(sig, type_dict):
    req, default, empty, klazz_schema = sig
    real_class = TypeFactory.new(type_dict, *klazz_schema)
    if not empty:
      return TypeSignature(real_class, default=real_class(default), required=req)
    else:
      return TypeSignature(real_class, required=req)

  def __hash__(self):
    return hash(
      self.klazz.serialize_type(),
      self.required,
      self.default,
      self.empty)

  def __eq__(self, other):
    return (self.klazz.serialize_type() == other.klazz.serialize_type() and
            self.required == other.required and
            self.default == other.default and
            self.empty == other.empty)

  def __ne__(self, other):
    return not (self == other)

  def __repr__(self):
    return 'TypeSignature(%s, required: %s, default: %s, empty: %s)' % (
      self.klazz.__name__, self.required, self.default, self.empty)

  @property
  def klazz(self):
    return self._cls

  @property
  def required(self):
    return self._required

  @property
  def default(self):
    return self._default

  @property
  def empty(self):
    return self._default is Empty

  @staticmethod
  def wrap(sig):
    """Convert a Python class into a type signature."""
    if isclass(sig) and issubclass(sig, Object):
      return TypeSignature(sig)
    elif isinstance(sig, TypeSignature):
      return sig


def Required(cls):
  """
    Helper to make composite types read succintly.  Wrap a type and make its
    specification required during type-checking of composite types.
  """
  return TypeSignature(cls, required=True)


def Default(cls, default):
  """
    Helper to make composite types read succintly.  Wrap a type and assign it a
    default if it is unspecified in the construction of the composite type.
  """
  return TypeSignature(cls, required=False, default=default)


class StructFactory(TypeFactory):
  PROVIDES = 'Struct'

  @staticmethod
  def create(type_dict, *type_parameters):
    """
      StructFactory.create(*type_parameters) expects:

        class name,
        ((binding requirement1,),
          (binding requirement2, bound_to_scope),
           ...),
        ((attribute_name1, attribute_sig1 (serialized)),
         (attribute_name2, attribute_sig2 ...),
         ...
         (attribute_nameN, ...))
    """
    name, parameters = type_parameters
    for param in parameters:
      assert isinstance(param, tuple)
    typemap = dict((attr, TypeSignature.deserialize(param, type_dict))
                   for attr, param in parameters)
    attributes = {'TYPEMAP': typemap}
    return TypeMetaclass(str(name), (Structural,), attributes)


class StructMetaclass(type):
  """
    Schema-extracting metaclass for Struct objects.
  """
  @staticmethod
  def attributes_to_parameters(attributes):
    parameters = []
    for attr_name, attr_value in attributes.items():
      sig = TypeSignature.wrap(attr_value)
      if sig:
        parameters.append((attr_name, sig.serialize()))
    return tuple(parameters)

  def __new__(mcs, name, parents, attributes):
    if any(parent.__name__ == 'Struct' for parent in parents):
      type_parameters = StructMetaclass.attributes_to_parameters(attributes)
      return TypeFactory.new({}, 'Struct', name, type_parameters)
    else:
      return type.__new__(mcs, name, parents, attributes)


StructMetaclassWrapper = StructMetaclass('StructMetaclassWrapper', (object,), {})
class Structural(Object, Type, Namable):
  """A Structural base type for composite objects."""
  __slots__ = ('_schema_data',)

  def __init__(self, *args, **kw):
    self._schema_data = frozendict((attr, value.default) for (attr, value) in self.TYPEMAP.items())
    for arg in args:
      if not isinstance(arg, Mapping):
        raise ValueError('Expected dictionary argument, got %s' % repr(arg))
      self._update_schema_data(**arg)
    self._update_schema_data(**copy.copy(kw))
    super(Structural, self).__init__()

  def get(self):
    return frozendict((k, v.get()) for k, v in self._schema_data.items() if v is not Empty)

  def _process_schema_attribute(self, attr, value):
    if attr not in self.TYPEMAP:
      raise AttributeError('Unknown schema attribute %s' % attr)
    schema_type = self.TYPEMAP[attr]
    if value is Empty:
      return Empty
    elif isinstance(value, schema_type.klazz):
      return value
    else:
      return schema_type.klazz(value)

  def _update_schema_data(self, **kw):
    for attr, value in kw.items():
      self._schema_data[attr] = self._process_schema_attribute(attr, value)

  def dup(self):
    return self.__class__(**self._schema_data)

  def __call__(self, **kw):
    new_self = self.copy()
    new_self._update_schema_data(**copy.copy(kw))
    return new_self

  def __hash__(self):
    return hash(self.get())

  def __eq__(self, other):
    if not isinstance(other, Structural): return False
    if self.TYPEMAP != other.TYPEMAP: return False
    si = self.interpolate()
    oi = other.interpolate()
    return si[0]._schema_data == oi[0]._schema_data

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (
      self.__class__.__name__,
      (',\n%s' % (' ' * (len(self.__class__.__name__) + 1))).join(
          '%s=%s' % (key, val) for key, val in si._schema_data.items() if val is not Empty)
    )

  def __getattr__(self, attr):
    if not hasattr(self, 'TYPEMAP'):
      raise AttributeError

    if attr.startswith('has_'):
      if attr[4:] in self.TYPEMAP:
        return lambda: self._schema_data[attr[4:]] != Empty

    if attr not in self.TYPEMAP:
      raise AttributeError("%s has no attribute %s" % (self.__class__.__name__, attr))

    return lambda: self.interpolate_key(attr)

  def check(self):
    for name, signature in self.TYPEMAP.items():
      if self._schema_data[name] is Empty and signature.required:
        return TypeCheck.failure('%s[%s] is required.' % (self.__class__.__name__, name))
      elif self._schema_data[name] is not Empty:
        type_check = self._schema_data[name].in_scope(*self.scopes()).check()
        if type_check.ok():
          continue
        else:
          return TypeCheck.failure('%s[%s] failed: %s' % (self.__class__.__name__, name,
            type_check.message()))
    return TypeCheck.success()

  @classmethod
  def _cast_scopes_to_child(cls, scopes):
    return tuple(Environment({'super': scope}) for scope in scopes)

  def _self_scope(self):
    return Environment(dict((key, value) for (key, value) in self._schema_data.items()
                       if value is not Empty))

  def scopes(self):
    self_scope = self._self_scope()
    return (Environment({'self': self_scope}), self_scope,) + self._scopes + (
        self._cast_scopes_to_child(self._scopes))

  def interpolate(self):
    unbound = set()
    interpolated_schema_data = {}
    scopes = self.scopes()
    for key, value in self._schema_data.items():
      if value is Empty:
        interpolated_schema_data[key] = Empty
      else:
        vinterp, vunbound = value.in_scope(*scopes).interpolate()
        unbound.update(vunbound)
        interpolated_schema_data[key] = vinterp
    return self.__class__(**interpolated_schema_data), list(unbound)

  def interpolate_key(self, attribute):
    if self._schema_data[attribute] is Empty:
      return Empty
    vinterp, _ = self._schema_data[attribute].in_scope(*self.scopes()).interpolate()
    return self._process_schema_attribute(attribute, vinterp)

  @classmethod
  def type_factory(cls):
    return 'Struct'

  @classmethod
  def type_parameters(cls):
    attrs = []
    if hasattr(cls, 'TYPEMAP'):
      attrs = sorted([(attr, sig.serialize()) for attr, sig in cls.TYPEMAP.items()])
    return (cls.__name__, tuple(attrs))

  @classmethod
  def _filter_against_schema(cls, values):
    result = {}
    for key, val in values.items():
      if key not in cls.TYPEMAP:
        continue
      if issubclass(cls.TYPEMAP[key].klazz, Structural):
        result[key] = cls.TYPEMAP[key].klazz._filter_against_schema(val)
      else:
        result[key] = val
    return result

  @classmethod
  def json_load(cls, fp, strict=False):
    return cls(json.load(fp) if strict else cls._filter_against_schema(json.load(fp)))

  @classmethod
  def json_loads(cls, json_string, strict=False):
    return cls(json.loads(json_string) if strict
               else cls._filter_against_schema(json.loads(json_string)))

  def json_dump(self, fp):
    d, _ = self.interpolate()
    return json.dump(d.get(), fp)

  def json_dumps(self):
    d, _ = self.interpolate()
    return json.dumps(d.get())

  def find(self, ref):
    if not ref.is_dereference():
      raise Namable.NamingError(self, ref)
    name = ref.action().value
    if name not in self.TYPEMAP or self._schema_data[name] is Empty:
      raise Namable.NotFound(self, ref)
    else:
      namable = self._schema_data[name]
      if ref.rest().is_empty():
        return namable.in_scope(*self.scopes())
      else:
        if not isinstance(namable, Namable):
          raise Namable.Unnamable(namable)
        else:
          return namable.in_scope(*self.scopes()).find(ref.rest())


class Struct(StructMetaclassWrapper, Structural):
  """
    Schema-based composite objects, e.g.

      class Employee(Struct):
        first = Required(String)
        last  = Required(String)
        email = Required(String)
        phone = String

      Employee(first = "brian", last = "wickman", email = "wickman@twitter.com").check()

    They're purely functional data structures and behave more like functors.
    In other words they're immutable:

      >>> brian = Employee(first = "brian")
      >>> brian(last = "wickman")
      Employee(last=String(wickman), first=String(brian))
      >>> brian
      Employee(first=String(brian))
  """
  pass

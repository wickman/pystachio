from collections import Mapping
import copy
from inspect import isclass

from pystachio.base import TypeCheck, Object, frozendict
from pystachio.schema import Schema
from pystachio.naming import Namable

class Empty(object):
  """The Empty sentinel representing an unspecified field."""
  pass

class TypeSignature(object):
  """
    Type metadata for composite type schemas.
  """

  def __init__(self, cls, required=False, default=Empty):
    assert isclass(cls)
    assert issubclass(cls, Object)
    if default is not Empty and not isinstance(default, cls):
      self._default = cls(default)
    else:
      self._default = default
    self._cls = cls
    self._required = required

  def __eq__(self, other):
    return (self.klazz == other.klazz and
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
  def parse(sig):
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


class StructMetaclass(type):
  """
    Schema-extracting metaclass for Struct objects.
  """

  @staticmethod
  def extract_typemap(attributes):
    typemap = {}
    for attr_name, attr_value in attributes.items():
      sig = TypeSignature.parse(attr_value)
      if sig: typemap[attr_name] = sig
    for extracted_attribute in typemap:
      attributes.pop(extracted_attribute)
    attributes['TYPEMAP'] = typemap
    return attributes

  def __new__(mcs, name, parents, attributes):
    augmented_attributes = StructMetaclass.extract_typemap(attributes)
    return type.__new__(mcs, name, parents, augmented_attributes)


class Struct(Object, Schema, Namable):
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
  __metaclass__ = StructMetaclass

  def __init__(self, *args, **kw):
    self._init_schema_data()
    for arg in args:
      if not isinstance(arg, Mapping):
        raise ValueError('Expected dictionary argument')
      self._update_schema_data(**arg)
    self._update_schema_data(**copy.deepcopy(kw))
    Object.__init__(self)

  def get(self):
    return frozendict((k, v.get()) for k, v in self._schema_data.items() if v is not Empty)

  def _schema_check(self, kw):
    for attr in kw:
      if attr not in self.TYPEMAP:
        raise AttributeError('Unknown schema attribute %s' % attr)

  def _init_schema_data(self):
    self._schema_data = {}
    for attr in self.TYPEMAP:
      self._schema_data[attr] = self.TYPEMAP[attr].default
    self._schema_data = frozendict(self._schema_data)

  def _update_schema_data(self, **kw):
    for attr in kw:
      if attr not in self.TYPEMAP:
        raise AttributeError('Unknown schema attribute %s' % attr)
      schema_type = self.TYPEMAP[attr]
      if kw[attr] is Empty:
        self._schema_data[attr] = Empty
      elif isinstance(kw[attr], schema_type.klazz):
        self._schema_data[attr] = kw[attr]
      else:
        self._schema_data[attr] = schema_type.klazz(kw[attr])

  def copy(self):
    new_object = self.__class__(**self._schema_data)
    new_object._scopes = copy.deepcopy(self.scopes())
    return new_object

  def __call__(self, **kw):
    new_self = self.copy()
    new_self._update_schema_data(**copy.deepcopy(kw))
    return new_self

  def __eq__(self, other):
    if not isinstance(other, Struct): return False
    if self.TYPEMAP != other.TYPEMAP: return False
    si = self.interpolate()
    oi = other.interpolate()
    return si[0]._schema_data == oi[0]._schema_data

  def __repr__(self):
    si, _ = self.interpolate()
    return '%s(%s)' % (
      self.__class__.__name__,
      ', '.join('%s=%s' % (key, val) for key, val in si._schema_data.items() if val is not Empty)
    )

  def check(self):
    for name, signature in self.TYPEMAP.items():
      if self._schema_data[name] is Empty and signature.required:
        return TypeCheck.failure('%s[%s] is required.' % (self.__class__.__name__, name))
      elif self._schema_data[name] is not Empty:
        type_check = self._schema_data[name].check()
        if type_check.ok():
          continue
        else:
          return TypeCheck.failure('%s[%s] failed: %s' % (self.__class__.__name__, name,
            type_check.message()))
    return TypeCheck.success()

  def interpolate(self):
    unbound = set()
    interpolated_schema_data = {}
    for key, value in self._schema_data.items():
      if value is Empty:
        interpolated_schema_data[key] = Empty
      else:
        vinterp, vunbound = value.in_scope(*self.scopes()).interpolate()
        unbound.update(vunbound)
        interpolated_schema_data[key] = vinterp
    return self.__class__(**interpolated_schema_data), list(unbound)

  @classmethod
  def schema_name(cls):
    return 'Struct'

  @classmethod
  def serialize_schema(cls):
    schemadict = {
      '__name__': cls.__name__,
      '__typemap__': {}
    }
    typemap = schemadict['__typemap__']
    for name, sig in cls.TYPEMAP.items():
      typemap[name] = (sig.required,
        sig.default.get() if not sig.empty else {},
        sig.empty, sig.klazz.serialize_schema())
    return (cls.schema_name(), schemadict)

  @staticmethod
  def deserialize_schema(schema):
    schema_name, schema_parameters = schema
    typemap = {}
    for name, sig in schema_parameters['__typemap__'].items():
      req, default, empty, klazz_schema = sig
      real_class = Schema.deserialize_schema(klazz_schema)
      if not empty:
        typemap[name] = TypeSignature(real_class, default=real_class(default), required=req)
      else:
        typemap[name] = TypeSignature(real_class, required=req)
    return StructMetaclass(schema_parameters['__name__'], (Struct,), typemap)

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

Schema.register_schema(Struct)

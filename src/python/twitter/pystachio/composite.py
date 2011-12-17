import copy
from inspect import isclass
from objects import (
  Empty,
  ObjectBase,
  TypeCheck)

class TypeSignature(object):
  """
    Type metadata for composite type schemas.
  """

  def __init__(self, cls, required=False, default=Empty):
    assert isclass(cls)
    assert issubclass(cls, ObjectBase)
    if default is not Empty and not isinstance(default, cls):
      self._default = cls(default)
    else:
      self._default = default
    self._cls = cls
    self._required = required

  def klazz(self):
    return self._cls

  def required(self):
    return self._required

  def default(self):
    return self._default

  @staticmethod
  def parse(sig):
    if isclass(sig) and issubclass(sig, ObjectBase):
      return TypeSignature(sig)
    elif isinstance(sig, TypeSignature):
      return sig

def Required(cls):
  return TypeSignature(cls, required=True)

def Default(cls, default):
  return TypeSignature(cls, required=False, default=default)


class CompositeMetaclass(type):
  """
    Schema-extracting metaclass for Composite objects.
  """

  @staticmethod
  def extract_schema(attributes):
    schema = {}
    for attr_name, attr_value in attributes.items():
      sig = TypeSignature.parse(attr_value)
      if sig: schema[attr_name] = sig
    for extracted_attribute in schema:
      attributes.pop(extracted_attribute)
    attributes['SCHEMA'] = schema
    return attributes

  def __new__(mcls, name, parents, attributes):
    augmented_attributes = CompositeMetaclass.extract_schema(attributes)
    return type.__new__(mcls, name, parents, augmented_attributes)


class Composite(ObjectBase):
  """
    Schema-based composite objects, e.g.

      class Employee(Composite):
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
  __metaclass__ = CompositeMetaclass

  def __init__(self, **kw):
    self._init_schema_data()
    self._update_schema_data(**copy.deepcopy(kw))
    ObjectBase.__init__(self)

  def _schema_check(self, kw):
    for attr in kw:
      if attr not in self.SCHEMA:
        raise AttributeError('Unknown schema attribute %s' % attr)

  def _init_schema_data(self):
    self._schema_data = {}
    for attr in self.SCHEMA:
      self._schema_data[attr] = self.SCHEMA[attr].default()

  def _update_schema_data(self, **kw):
    for attr in kw:
      if attr not in self.SCHEMA:
        raise AttributeError('Unknown schema attribute %s' % attr)
      schema_type = self.SCHEMA[attr]
      if kw[attr] is Empty:
        self._schema_data[attr] = Empty
      elif isinstance(kw[attr], schema_type.klazz()):
        self._schema_data[attr] = kw[attr]
      else:
        self._schema_data[attr] = schema_type.klazz()(kw[attr])

  def copy(self):
    new_object = self.__class__(**self._schema_data)
    new_object._environment = copy.deepcopy(self._environment)
    return new_object

  def __call__(self, **kw):
    new_self = self.copy()
    new_self._update_schema_data(**copy.deepcopy(kw))
    return new_self

  def __eq__(self, other):
    if not isinstance(other, Composite): return False
    if self.SCHEMA != other.SCHEMA: return False
    si = self.interpolate()
    oi = other.interpolate()
    return si[0]._schema_data == oi[0]._schema_data

  def __repr__(self):
    return '%s(%s)' % (
      self.__class__.__name__,
      ', '.join('%s=%s' % (key, val) for key, val in self._schema_data.items() if val is not Empty)
    )

  def check(self):
    for name, signature in self.SCHEMA.items():
      if self._schema_data[name] is Empty and signature.required():
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
        vinterp, vunbound = value.in_scope(self.environment()).interpolate()
        unbound.update(vunbound)
        interpolated_schema_data[key] = vinterp
    return self.__class__(**interpolated_schema_data), list(unbound)

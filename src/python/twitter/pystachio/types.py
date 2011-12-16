import copy
import types

from collections import Iterable, Mapping
from inspect import isclass
from .objects import ObjectEnvironment


class Empty(object):
  """The Empty sentinel representing an unspecified field."""
  pass


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


class ObjectBase(object):
  """
    ObjectBase base class, encapsulating a set of variable bindings scoped to this object.
  """

  @classmethod
  def checker(cls, obj):
    raise NotImplementedError

  def __init__(self):
    self._environment = ObjectEnvironment()

  def copy(self):
    """
      Return a copy of this object.
    """
    raise NotImplementedError

  def bind(self, *args, **kw):
    """
      Bind environment variables into this object's scope.
    """
    new_self = self.copy()
    binding_environment = ObjectEnvironment(*args, **kw)
    ObjectEnvironment.merge(new_self._environment, binding_environment)
    return new_self

  def check(self):
    """
      Perform post-bind type checking.
    """
    return self.checker(self)

  def interpolate(self):
    """
      Return a copy of this object interpolated in the context of self._environment.
    """
    raise NotImplementedError


class Object(ObjectBase):
  """
    A simply-valued object.
  """
  class CoercionError(Exception):
    def __init__(self, src, dst):
      Exception.__init__(self, "Cannot coerce %s to %s" % (src, dst.__name__))

  def __init__(self, value):
    self._value = copy.deepcopy(value)
    ObjectBase.__init__(self)

  def copy(self):
    new_object = self.__class__(self._value)
    new_object._environment = copy.deepcopy(self._environment)
    return new_object

  def __eq__(self, other):
    return self.__class__ == other.__class__ and self._value == other._value

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, self._value)


class String(Object):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, String):
      return TypeCheck.failure("%s is not a subclass of String" % obj)
    if isinstance(obj._value, str):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a string" % repr(obj._value))

  @classmethod
  def coerce(cls, value):
    ACCEPTED_SOURCE_TYPES = (int, float, basestring)
    if not isinstance(value, ACCEPTED_SOURCE_TYPES):
      raise Object.CoercionError(value, cls)
    return str(value)


class Integer(Object):
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
      raise Object.CoercionError(value, cls)
    try:
      return int(value)
    except ValueError:
      raise Object.CoercionError(value, cls)


class Float(Object):
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
      raise Object.CoercionError(value, cls)
    try:
      return float(value)
    except ValueError:
      raise Object.CoercionError(value, cls)



class List(Object):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, List):
      return TypeCheck.failure("%s is not a subclass of List" % obj)
    if isinstance(obj._value, Iterable):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not an iterable" % repr(obj._value))


class Map(Object):
  @classmethod
  def checker(cls, obj):
    if not isinstance(obj, Map):
      return TypeCheck.failure("%s is not a subclass of Map" % obj)
    if isinstance(obj._value, Mapping):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a mapping" % repr(obj._value))



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
          return TypeCheck.failure('%s[%s] failed: %s' % (self.__class__.__name__, name, type_check.message()))
    return TypeCheck.success()

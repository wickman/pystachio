import copy
import types

from collections import Iterable, Mapping
from inspect import isclass
from .objects import ObjectEnvironment


class Empty(object):
  pass


class TypeCheck(object):
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
  @classmethod
  def checker(cls, obj):
    raise NotImplementedError
  
  def __init__(self):
    self._environment = ObjectEnvironment()
  
  def copy(self):
    raise NotImplementedError

  def bind(self, *args, **kw):
    new_self = self.copy()
    binding_environment = ObjectEnvironment(*args, **kw)
    ObjectEnvironment.merge(new_self._environment, binding_environment)
    return new_self
  
  def check(self):
    return self.checker(self)


class Object(ObjectBase):
  def __init__(self, value):
    self._value = copy.deepcopy(value)
    ObjectBase.__init__(self)
  
  def copy(self):
    new_object = self.__class__(self._value)
    new_object._environment = copy.deepcopy(self._environment)
    return new_object

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


class Integer(Object):
  @classmethod
  def checker(cls, obj):
    if isinstance(obj._value, int):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not an integer" % repr(obj._value))


class Float(Object):
  @classmethod
  def checker(cls, obj):
    if isinstance(obj._value, float):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a float" % repr(obj._value))


class List(Object):
  @classmethod
  def checker(cls, obj):
    if isinstance(obj._value, Iterable):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not an iterable" % repr(obj._value))


class Map(Object):
  @classmethod
  def checker(cls, obj):
    if isinstance(obj._value, Mapping):
      return TypeCheck.success()
    else:
      return TypeCheck.failure("%s not a mapping" % repr(obj._value))



class TypeSignature(object):
  def __init__(self, cls, required=False, default=Empty):
    assert isclass(cls)
    assert issubclass(cls, ObjectBase)
    self._cls = cls
    self._required = required
    self._default = default

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
  

class CompositeObject(ObjectBase):
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
      if isinstance(kw[attr], schema_type.klazz()):
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

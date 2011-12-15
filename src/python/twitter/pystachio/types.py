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
  
  def empty(self):
    raise NotImplementedError

  def _optional_check(self):
    if self.empty():
      return TypeCheck.success()
    else:
      return self.checker(self)

  def _required_check(self):
    return self.checker(self)

  check = _optional_check
    

class Object(ObjectBase):
  def __init__(self, value=Empty):
    self._value = copy.deepcopy(value)
    ObjectBase.__init__(self)
  
  def copy(self):
    new_object = self.__class__(self._value)
    new_object._environment = copy.deepcopy(self._environment)
    return new_object

  def empty(self):
    return self._value is Empty

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, self._value)


class String(Object):
  @classmethod
  def checker(cls, obj):
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



def Required(cls):
  # takes an Object and creates a new one whose
  # type checker method [cls.BASE_CHECKER] is not skipped if
  # an object is unassigned.
  assert isclass(cls)
  assert issubclass(cls, ObjectBase)
  if cls.check == cls._required_check:
    return cls
  else:
    # Ack, what is with the SCHEMA addition?
    updated_attributes = { 'check': cls._required_check }
    print 'Augmenting cls: %s' % cls
    if hasattr(cls, 'SCHEMA'):
      updated_attributes.update(copy.deepcopy(cls.SCHEMA))
    return type.__new__(type, 'Required%s' % cls.__name__, (cls,), updated_attributes)


def Default(cls, *args, **kw):
  # takes an Object and creates a new one whose __init__ method is
  # passed the *args,**kw should it otherwise be passed an empty param list
  pass



class CompositeMetaclass(type):
  @staticmethod
  def extract_schema(attributes):
    schema = {}
    for attr_name, attr_value in attributes.items():
      if isclass(attr_value) and issubclass(attr_value, ObjectBase):
        schema[attr_name] = attr_value
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
    self._schema_check(kw)
    self._schema_data = copy.deepcopy(kw)
    ObjectBase.__init__(self)
  
  def _schema_check(self, kw):
    for attr in kw:
      if attr not in self.SCHEMA:
        raise AttributeError('Unknown schema attribute %s' % attr)

  def copy(self):
    new_object = self.__class__(**self._schema_data)
    new_object._environment = copy.deepcopy(self._environment)
    return new_object

  def __call__(self, **kw):
    self._schema_check(kw)
    new_self = self.copy()
    new_self._schema_data.update(copy.deepcopy(kw))
    return new_self

  def __repr__(self):
    return '%s(%s)' % (
      self.__class__.__name__,
      ', '.join('%s=%s' % (key, val) for key, val in self._schema_data.items())
    )

  def empty(self):
    return self._schema_data == {}

  def _recursive_check(self):
    for attr_name, attr_type in self.SCHEMA.items():
      if attr_name in self._schema_data:
        if issubclass(attr_type, CompositeObject):
          if not self._schema_data[attr_name].check().ok():
            return TypeCheck.failure('%s[%s] failed: %s' % (
              self.__class__.__name__, attr_name,
              self._schema_data[attr_name].check().message()))
        else:
          if not attr_type(self._schema_data[attr_name]).check().ok():
            return TypeCheck.failure('%s[%s] failed: %s' % (
              self.__class__.__name__, attr_name,
              attr_type(self._schema_data[attr_name]).check().message()))
      else:
        if not attr_type().check().ok():
          return TypeCheck.failure('%s[%s] failed: %s' % (
            self.__class__.__name__, attr_name,
            attr_type().check().message()))
    return TypeCheck.success()

  def _optional_check(self):
    if self.empty():
      return TypeCheck.success()
    else:
      return self._recursive_check()
  
  def _required_check(self):
    return self._recursive_check()
  
  check = _optional_check

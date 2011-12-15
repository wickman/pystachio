import copy

from collections import Iterable, Mapping
from inspect import isclass
from .objects import ObjectEnvironment

class Empty(object):
  pass


class Type(object):
  PARAMETERS = ('required', 'default',)

  @classmethod
  def checker(cls):
    raise NotImplementedError

  def __init__(self, required=False, default=Empty):
    self._required = required
    self._default = default

  def required(self):
    return self._required

  def check(self, value=Empty):
    if self.required() or value is not Empty:
      return self.checker()(value)
    else:
      return True

class String(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, str)
    return _checker


class Integer(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, int)
    return _checker


class Float(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, float)
    return _checker


class List(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, Iterable)
    return _checker


class Map(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, Mapping)
    return _checker


class CompositeMetaclass(type):
  @staticmethod
  def extract_schema(attributes):
    schema = {}
    for attr_name, attr_value in attributes.items():
      if isinstance(attr_value, Type):
        schema[attr_name] = attr_value
      elif isclass(attr_value) and issubclass(attr_value, Type):
        schema[attr_name] = attr_value()
    for extracted_attribute in schema:
      attributes.pop(extracted_attribute)
    return (schema, attributes)

  def __new__(mcls, name, parents, attributes):
    augmented_attributes = copy.deepcopy(attributes)
    schema, augmented_attributes = CompositeMetaclass.extract_schema(attributes)
    augmented_attributes['SCHEMA'] = schema
    return type.__new__(mcls, name, parents, augmented_attributes)


class Composite(Type):
  __metaclass__ = CompositeMetaclass

  def __init__(self, **kw):
    self._schema_data = copy.deepcopy(kw)
    self._environment = ObjectEnvironment()
    type_parameters = dict((param, self._schema_data.pop(param))
      for param in Type.PARAMETERS if param in self._schema_data)
    Type.__init__(self, type_parameters)
  
  def _copy(self):
    new_object = self.__class__(**self._schema_data)
    new_object._environment = copy.deepcopy(self._environment)
    return new_object

  def bind(self, *args, **kw):
    new_self = self._copy()
    binding_environment = ObjectEnvironment(*args, **kw)
    ObjectEnvironment.merge(new_self._environment, binding_environment)
    return new_self
  
  def __call__(self, **kw):
    new_self = self._copy()
    for attr in kw:
      if attr not in self.SCHEMA:
        raise AttributeError('Unknown schema attribute %s' % attr)
      new_self._schema_data[attr] = kw[attr]
    return new_self

  def __repr__(self):
    return '%s(%s)' % (
      self.__class__.__name__,
      ', '.join('%s=%s' % (key, val) for key, val in self._schema_data.items())
    )

  @classmethod
  def checker(cls):
    def _checker(value):
      if not isinstance(value, cls):
        return False
      for attr_name, attr_type in cls.SCHEMA.items():
        if attr_name in value._schema_data:
          if not attr_type.check(value._schema_data[attr_name]):
            return False
        else:
          if not attr_type.check():
            return False
      return True
    return _checker


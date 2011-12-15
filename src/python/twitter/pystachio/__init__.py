import copy
from inspect import isclass
import re
from .types import Type, Empty

class ObjectId(object):
  _COMPONENT_RE = re.compile(r'^\w+$')
  _COMPONENT_SEPARATOR = '.'

  class InvalidObjectIdError(Exception): pass
  class UnboundObjectId(Exception): pass
    
  def __init__(self, address):
    self._address = address
    ObjectId.raise_if_invalid(address)
  
  def address(self):
    return self._address
  
  def components(self):
    return self._address.split(self._COMPONENT_SEPARATOR)
  
  @staticmethod
  def raise_if_invalid(oid):
    for component in oid.components():
      if not ObjectId._COMPONENT_RE.match(component):
        raise ObjectId.InvalidObjectIdError("Invalid address: %s at %s" % (
          oid.address(), component))
  
  def __repr__(self):
    return 'ObjectId(%s)' % self._address
  
  def __eq__(self, other):
    return self._address == other._address
  
  @staticmethod
  def interpolate(oid, oenv):
    for component in oid.components():
      if component not in oenv:
        raise ObjectId.UnboundObjectId("%s not in %s" % (component, oenv))
      else:
        oenv = oenv[component]
    return oenv

class ObjectMustacheParser(object):
  _ADDRESS_DELIMITER = '&'
  _MUSTACHE_RE = re.compile(r"{{(%c)?([^{}]+?)\1?}}" % _ADDRESS_DELIMITER)

  @staticmethod
  def split(string):
    splits = ObjectMustacheParser._MUSTACHE_RE.split(string)
    first_split = splits.pop(0)
    outsplits = [first_split] if first_split else []
    assert len(splits) % 3 == 0
    for k in range(0, len(splits), 3):
      if splits[k] == ObjectMustacheParser._ADDRESS_DELIMITER:
        outsplits.append('{{%s}}' % splits[k+1])
      elif splits[k] == None:
        outsplits.append(ObjectId(splits[k+1]))
      else:
        raise Exception("Unexpected parsing error in Mustache regular expression, splits[%s] = '%s'" % (
          k, splits[k]))
      if splits[k+2]:
        outsplits.append(splits[k+2])
    return outsplits

class ObjectEnvironment(dict):
  """
    Need an attribute bundle that works something like this:
    
      Stores {
        'daemon': {
          'id': 1234,
          'name': 'oh baby'
        },
        'mesos': {
          'datacenter': 'smf1-prod',
          'cluster': {
            'slaves': 1235,
            'executors': 1358,
            ...
          }
        }
      }
      
      Then attributes.update(mesos = { 'cluster': { 'nodes': 1325 } })
        => recursively dives down and replaces only leaves.
      
      Furthermore, needs to be able to
      scope1.merge(scope2).merge(scope3).evaluate(mustache expression)
  """

  def __init__(self, *dictionaries, **names):
    env = {}
    for d in dictionaries:
      ObjectEnvironment.merge(env, d)
    ObjectEnvironment.merge(env, names)
    dict.__init__(self, env)
  
  @staticmethod
  def merge(env1, env2):
    for key in env2:
      if key not in env1:
        env1[key] = env2[key]
      else:
        if isinstance(env1[key], dict) and isinstance(env2[key], dict):
          ObjectEnvironment.merge(env1[key], env2[key])
        else:
          env1[key] = env2[key]


class ObjectMetaclass(type):
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
    schema, augmented_attributes = ObjectMetaclass.extract_schema(attributes)
    augmented_attributes['SCHEMA'] = schema
    return type.__new__(mcls, name, parents, augmented_attributes)


class Object(Type):
  __metaclass__ = ObjectMetaclass

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
          if not attr_type.check(Empty):
            return False
      return True
    return _checker

from inspect import isclass

class SchemaTrait(object):
  _SCHEMA_MAP = {}

  @classmethod
  def schema_name(cls):
    raise NotImplementedError

  @classmethod
  def serialize_schema(cls):
    """Given a class, serialize its schema."""
    raise NotImplementedError

  @staticmethod
  def deserialize_schema(schema):
    schema_cls = SchemaTrait.get_schema(schema)
    schema_name, schema_parameters = schema
    if issubclass(schema_cls, Schema):
      return schema_cls.deserialize_schema(schema)
    elif issubclass(schema_cls, Schemaless):
      return schema_cls
    else:
      raise ValueError("What are you smoking?")

  @staticmethod
  def register_schema(cls):
    assert isclass(cls)
    assert issubclass(cls, SchemaTrait)
    SchemaTrait._SCHEMA_MAP[cls.schema_name()] = cls

  @staticmethod
  def get_schema(schema_tuple):
    name, _ = schema_tuple
    assert name in SchemaTrait._SCHEMA_MAP, 'Unknown schema: %s' % name
    return SchemaTrait._SCHEMA_MAP[name]

class Schemaless(SchemaTrait):
  @classmethod
  def serialize_schema(cls):
    return (cls.schema_name(), None)

class Schema(SchemaTrait):
  pass

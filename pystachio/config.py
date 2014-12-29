import os
from functools import reduce

from .compatibility import Compatibility

try:
  import pkg_resources
except ImportError:
  pkg_resources = None


def relativize(from_path, include_path):
  return os.path.join(os.path.dirname(from_path), include_path)


class ConfigContext(object):
  ROOT = ''

  # Make JSON-friendly keys -- since JSON can't encode tuples as dictionary keys.
  @classmethod
  def key(cls, from_path, include_string):
    return '\0'.join([from_path, include_string])

  @classmethod
  def from_key(cls, key):
    return key.split('\0')

  def __init__(self, environment, loadables):
    self.environment = environment
    self.loadables = loadables

  def compile(self, from_path, include_string, data):
    self.loadables[self.key(from_path, include_string)] = data
    Compatibility.exec_function(compile(data, include_string, 'exec'), self.environment)


class ConfigExecutor(object):
  ROOT = ConfigContext.ROOT

  @classmethod
  def matches(cls, loadable):
    return False

  @classmethod
  def get(cls, loadable):
    """return the include function and the root include object."""
    raise NotImplementedError


class FileExecutor(ConfigExecutor):
  @classmethod
  def matches(cls, loadable):
    return isinstance(loadable, Compatibility.stringy) and os.path.isfile(loadable)

  @classmethod
  def compile_into(cls, context, from_path, config_file):
    actual_file = relativize(from_path, config_file)
    with open(actual_file) as fp:
      context.compile(from_path, config_file, fp.read())

  @classmethod
  def get(cls, loadable):
    deposit_stack = [cls.ROOT]
    def ast_executor(config_file, context):
      from_path = deposit_stack[-1]
      actual_file = relativize(from_path, config_file)
      deposit_stack.append(actual_file)
      cls.compile_into(context, from_path, config_file)
      deposit_stack.pop()
    return ast_executor, loadable


class ResourceExecutor(FileExecutor):
  @classmethod
  def resource_exists(cls, loadable):
    if pkg_resources is None:
      return False
    module_base, module_file = os.path.split(loadable)
    module_base = module_base.replace(os.sep, '.')
    try:
      return pkg_resources.resource_exists(module_base, module_file) and (
          not pkg_resources.resource_isdir(module_base, module_file))
    except (ValueError, ImportError):
      return False

  @classmethod
  def matches(cls, loadable):
    return isinstance(loadable, Compatibility.stringy) and cls.resource_exists(loadable)

  @classmethod
  def compile_into(cls, context, from_path, config_file):
    actual_file = relativize(from_path, config_file)
    module_base, module_file = os.path.split(actual_file)
    module_base = module_base.replace(os.sep, '.')
    context.compile(from_path, config_file,
        pkg_resources.resource_string(module_base, module_file))


class LoadableMapExecutor(ConfigExecutor):
  @classmethod
  def matches(cls, loadable):
    return isinstance(loadable, dict)

  @classmethod
  def find_root_file(cls, loadable):
    for key in loadable.keys():
      from_file, config_file = ConfigContext.from_key(key)
      if from_file == cls.ROOT:
        return config_file

  @classmethod
  def from_filename(cls, stack):
    return reduce(relativize, stack, '')

  @classmethod
  def get(cls, loadable):
    deposit_stack = [cls.ROOT]

    def ast_executor(config_file, context):
      from_file = cls.from_filename(deposit_stack)
      deposit_stack.append(config_file)
      context.compile(from_file, config_file, loadable[ConfigContext.key(from_file, config_file)])
      deposit_stack.pop()

    return ast_executor, cls.find_root_file(loadable)


class FilelikeExecutor(ConfigExecutor):
  @classmethod
  def matches(cls, loadable):
    return hasattr(loadable, 'read') and callable(loadable.read)

  @classmethod
  def get(cls, loadable):
    def ast_executor(config, context):
      if config is not loadable:
        raise ValueError('You may not include() anything from filelike objects.')
      context.compile(cls.ROOT, '<resource: %s>' % loadable, loadable.read())
    return ast_executor, loadable


class Config(object):
  class Error(Exception): pass
  class InvalidConfigError(Error): pass
  class NotFound(Error): pass

  DEFAULT_SCHEMA = 'from pystachio import *'
  EXECUTORS = [
    FileExecutor,
    ResourceExecutor,
    FilelikeExecutor,
    LoadableMapExecutor
  ]
  ROOT = None

  @classmethod
  def choose_executor(cls, obj):
    for executor in cls.EXECUTORS:
      if executor.matches(obj):
        return executor.get(obj)
    raise cls.NotFound('Could not load resource %s' % obj)

  @classmethod
  def load_schema(cls, environment, schema=None):
    Compatibility.exec_function(
        compile(schema or cls.DEFAULT_SCHEMA, "<exec_function>", "exec"), environment)

  def __init__(self, loadable, schema=None):
    self._environment = {}
    self._loadables = {}
    self.load_schema(self._environment, schema)
    root_executor, initial_config = self.choose_executor(loadable)
    context = ConfigContext(self._environment, self._loadables)
    self._environment.update(include=lambda fn: root_executor(fn, context))
    try:
      root_executor(initial_config, context)
    except (SyntaxError, ValueError) as e:
      raise self.InvalidConfigError(str(e))

  @property
  def loadables(self):
    return self._loadables

  @property
  def environment(self):
    return self._environment

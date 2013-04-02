import copy
import json
import os
import re

from .compatibility import Compatibility
from .naming import Ref

try:
  import pkg_resources
except ImportError:
  pkg_resources = None


class ConfigLoader(object):
  class Error(Exception): pass
  class InvalidConfigError(Error): pass
  class NotFound(Error): pass

  @classmethod
  def compile_into(cls, data, data_name, environment):
    try:
      Compatibility.exec_function(compile(data, data_name, 'exec'), environment)
    except SyntaxError as e:
      raise cls.InvalidConfigError(str(e))

  @classmethod
  def fp_executor(cls):
    def ast_executor(fp, env):
      if hasattr(fp, 'read') and callable(fp.read):
        cls.compile_into(fp.read(), '<resource: %s>' % fp, env)
      else:
        raise cls.InvalidConfigError('Configurations loaded from file cannot include other files.')
    return ast_executor

  @classmethod
  def file_executor(cls, filename):
    deposit_stack = [os.path.dirname(filename)]
    def ast_executor(config_file, env):
      actual_file = os.path.join(deposit_stack[-1], config_file)
      deposit_stack.append(os.path.dirname(actual_file))
      with open(actual_file) as fp:
        cls.compile_into(fp.read(), actual_file, env)
      deposit_stack.pop()
    return ast_executor

  @classmethod
  def resource_exists(cls, filename):
    if pkg_resources is None:
      return False
    module_base, module_file = os.path.split(filename)
    module_base = module_base.replace(os.sep, '.')
    try:
      return pkg_resources.resource_exists(module_base, module_file) and (
          not pkg_resources.resource_isdir(module_base, module_file))
    except (ValueError, ImportError):
      return False

  @classmethod
  def module_executor(cls, filename):
    deposit_stack = [os.path.dirname(filename)]
    def ast_executor(config_file, env):
      actual_file = os.path.join(deposit_stack[-1], config_file)
      deposit_stack.append(os.path.dirname(actual_file))
      module_base, module_file = os.path.split(actual_file)
      module_base = module_base.replace(os.sep, '.')
      cls.compile_into(pkg_resources.resource_string(module_base, module_file), actual_file, env)
      deposit_stack.pop()
    return ast_executor

  @classmethod
  def choose_executor_and_base(cls, obj):
    if isinstance(obj, Compatibility.string):
      if os.path.isfile(obj):
        return cls.file_executor(obj), os.path.basename(obj)
      elif cls.resource_exists(obj):
        return cls.module_executor(obj), os.path.basename(obj)
    elif hasattr(obj, 'read') and callable(obj.read):
      return cls.fp_executor(), obj
    raise cls.NotFound('Could not load resource %s' % obj)

  def __init__(self, schema=None, matchers=()):
    self._schema = schema or 'from pystachio import *'
    self._environment = {}
    Compatibility.exec_function(compile(self._schema, "<exec_function>", "exec"), self._environment)
    self._matchers = matchers

  def load(self, loadable):
    """
      Load a loadable object.  A loadable object may be one of:
        - a file-like object
        - a file path
        - a zipimported file path
    """
    environment = copy.copy(self._environment)
    ast_executor, loadable_base = self.choose_executor_and_base(loadable)
    environment.update(include=lambda fn: ast_executor(fn, environment))
    ast_executor(loadable_base, environment)
    return environment

  def reify(self, obj):
    return obj.interpolate(matchers=self._matchers)

import contextlib
from io import BytesIO
import json
import os
import shutil
import tempfile
import textwrap

from pystachio.config import Config, ConfigContext

import pytest


@contextlib.contextmanager
def make_layout(layout):
  tempdir = tempfile.mkdtemp()

  for filename, file_content in layout.items():
    real_path = os.path.join(tempdir, filename)
    try:
      os.makedirs(os.path.dirname(real_path))
    except OSError:
      # assume EEXIST
      pass
    with open(real_path, 'w') as fp:
      fp.write(textwrap.dedent(file_content))

  try:
    yield tempdir
  finally:
    shutil.rmtree(tempdir)


@contextlib.contextmanager
def pushd(dirname):
  cwd = os.getcwd()
  os.chdir(dirname)
  try:
    yield
  finally:
    os.chdir(cwd)


def test_includes():
  layout = {
    'conf/a.config':
      """
      include("../b.config")
      a = b
      """,

    'b.config':
      """
      b = "Hello"
      """
  }

  def k(a, b):
    return ConfigContext.key(a, b)

  with make_layout(layout) as td:
    with pushd(td):
      config = Config('conf/a.config')
      assert config.environment['a'] == 'Hello'
      assert config.environment['b'] == 'Hello'
      assert config.loadables[k('', 'conf/a.config')] == textwrap.dedent(layout['conf/a.config'])
      assert config.loadables[k('conf/a.config', '../b.config')] == (
          textwrap.dedent(layout['b.config']))

  config2 = Config(config.loadables)
  assert config.environment['a'] == config2.environment['a']
  assert config.environment['b'] == config2.environment['b']
  assert config.loadables == config2.loadables

  config3 = Config(json.loads(json.dumps(config.loadables)))
  assert config.environment['a'] == config3.environment['a']
  assert config.environment['b'] == config3.environment['b']
  assert config.loadables == config3.loadables

  with make_layout(layout) as td:
    config = Config(os.path.join(td, 'conf/a.config'))
  config2 = Config(config.loadables)
  assert config.environment['a'] == config2.environment['a']
  assert config.environment['b'] == config2.environment['b']
  assert config.loadables == config2.loadables


def test_transitive_includes():
  layout = {
    'conf/a.config':
      """
      include("../b.config")
      a = b
      """,

    'b.config':
      """
      include('common/c.config')
      b = "Hello"
      """,
    
    'common/c.config':
      """
      c = "Blerp"
      """
  }

  def k(a, b):
    return ConfigContext.key(a, b)

  with make_layout(layout) as td:
    with pushd(td):
      config = Config('conf/a.config')
      assert config.environment['a'] == 'Hello'
      assert config.environment['b'] == 'Hello'
      assert config.environment['c'] == 'Blerp'


def test_filelike_config():
  foo = b"a = 'Hello'"
  config = Config(BytesIO(foo))
  assert config.environment['a'] == 'Hello'
  print(config.loadables)

  config2 = Config(config.loadables)
  assert config2.environment['a'] == 'Hello'

  foo = b"include('derp')\na = 'Hello'"
  with pytest.raises(Config.InvalidConfigError):
    config = Config(BytesIO(foo))


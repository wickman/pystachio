import contextlib
import json
import os
import shutil
import tempfile
import textwrap
from io import BytesIO

import pytest

from pystachio.config import Config, ConfigContext


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
    'dir1/dir2/a.config':
      """
      include("../b.config")
      a = b
      """,

    'dir1/b.config':
      """
      include("../c.config")
      b = "Hello"
      """,

    'c.config':
      """
      c = "Goodbye"
      """
  }

  def k(a, b):
    return ConfigContext.key(a, b)

  with make_layout(layout) as td:
    with pushd(td):
      config = Config('dir1/dir2/a.config')
      assert config.environment['a'] == 'Hello'
      assert config.environment['b'] == 'Hello'
      assert config.environment['c'] == 'Goodbye'
      assert config.loadables[k('', 'dir1/dir2/a.config')] == textwrap.dedent(
          layout['dir1/dir2/a.config'])
      assert config.loadables[k('dir1/dir2/a.config', '../b.config')] == (
          textwrap.dedent(layout['dir1/b.config']))

  config2 = Config(config.loadables)
  assert config.environment['a'] == config2.environment['a']
  assert config.environment['b'] == config2.environment['b']
  assert config2.environment['c'] == 'Goodbye'
  assert config.loadables == config2.loadables

  config3 = Config(json.loads(json.dumps(config.loadables)))
  assert config.environment['a'] == config3.environment['a']
  assert config.environment['b'] == config3.environment['b']
  assert config3.environment['c'] == 'Goodbye'
  assert config.loadables == config3.loadables

  with make_layout(layout) as td:
    config = Config(os.path.join(td, 'dir1/dir2/a.config'))
  config2 = Config(config.loadables)
  assert config.environment['a'] == config2.environment['a']
  assert config.environment['b'] == config2.environment['b']
  assert config.loadables == config2.loadables


def test_filelike_config():
  foo = b"a = 'Hello'"
  config = Config(BytesIO(foo))
  assert config.environment['a'] == 'Hello'

  config2 = Config(config.loadables)
  assert config2.environment['a'] == 'Hello'

  foo = b"include('derp')\na = 'Hello'"
  with pytest.raises(Config.InvalidConfigError):
    config = Config(BytesIO(foo))

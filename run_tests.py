import contextlib
from itertools import chain
import os
import subprocess
import sys

@contextlib.contextmanager
def chdir(target):
  cwd = os.getcwd()
  os.chdir(target)
  try:
    yield
  finally:
    os.chdir(cwd)

def get_virtualenvs(basedir):
  with chdir(basedir):
    for path in os.listdir('.'):
      if path.startswith('.virtualenv-'):
        yield os.path.join(basedir, path)

def main(args):
  basedir = os.path.dirname(os.path.realpath(args[0]))
  virtualenvs = list(get_virtualenvs(basedir))
  assert len(virtualenvs) > 0

  def gen_shell_command():
    py_test = os.path.join(virtualenvs[1], 'bin', 'py.test')
    tx_targets = [['--tx', 'popen//python=%s' % os.path.join(ve, 'bin', 'python')]
                  for ve in virtualenvs]
    return ([py_test, '--dist=load'] +
            list(chain(*tx_targets)) +
            ['--cov=pystachio', '--cov-report=term-missing', '--cov-report=html'])

  os.putenv('PYTHONPATH', basedir)
  subprocess.call(gen_shell_command())

if __name__ == '__main__':
  main(sys.argv)


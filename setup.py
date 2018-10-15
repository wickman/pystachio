#!/usr/bin/env python
from setuptools import Command, find_packages, setup

version = '0.8.4'


class PyTest(Command):
  user_options = []

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    import sys, subprocess
    try:
      from py import test as pytest
    except ImportError:
      raise Exception('Running tests requires pytest.')
    errno = subprocess.call([sys.executable, '-m', 'py.test'])
    raise SystemExit(errno)


setup(
  name                 = 'pystachio',
  version              = version,
  description          = 'type-checked dictionary templating library',
  url                  = 'http://github.com/wickman/pystachio',
  author               = 'Brian Wickman',
  author_email         = 'wickman@gmail.com',
  license              = 'MIT',
  packages             = find_packages(),
  py_modules           = ['pystachio'],
  zip_safe             = True,
  cmdclass             = {
    'test': PyTest
  },
  scripts              = [
    'bin/pystachio_repl'
  ],
  classifiers          = [
    'Programming Language :: Python',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
  ],
)

__author__ = 'Brian Wickman'
__version__ = '0.1.0'
__license__ = 'MIT'

from sys import version_info
from numbers import (Real, Integral)

from pystachio.typing import (
  Type,
  TypeCheck,
  TypeFactory)

class Types(object):
  """2.x + 3.x compatibility"""
  stringy = (str,)
  if version_info[0] == 2:
    stringy = (str, unicode)
  integer = (Integral,)
  real = (Real,)
  numeric = integer + real
  PY2 = version_info[0] == 2
  PY3 = version_info[0] == 3

from pystachio.base import Environment
from pystachio.parsing import MustacheParser
from pystachio.naming import Namable, Ref

from pystachio.basic import (
  Float,
  Integer,
  String)

from pystachio.container import (
  List,
  Map)

from pystachio.composite import (
  Empty,
  Struct,
  Required,
  Default)

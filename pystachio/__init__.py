__author__ = 'Brian Wickman'
__version__ = '0.5.2'
__license__ = 'MIT'

import sys
if sys.version_info < (2, 6, 5):
  raise ImportError("pystachio requires Python >= 2.6.5")

from pystachio.typing import (
  Type,
  TypeCheck,
  TypeFactory)

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
  Default,
  Empty,
  Provided,
  Required,
  Struct)

from sys import version_info
from numbers import (Real, Integral)

class Compatibility(object):
  """2.x + 3.x compatibility"""
  stringy = (str,)
  if version_info[0] == 2:
    stringy = (str, unicode)
  integer = (Integral,)
  real = (Real,)
  numeric = integer + real
  PY2 = version_info[0] == 2
  PY3 = version_info[0] == 3

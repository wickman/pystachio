from numbers import Integral, Real
from sys import version_info


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
  if PY3:
    @staticmethod
    def exec_function(ast, globals_map):
      locals_map = globals_map
      exec(ast, globals_map, locals_map)
      return locals_map
  else:
    eval(compile(
"""
@staticmethod
def exec_function(ast, globals_map):
  locals_map = globals_map
  exec ast in globals_map, locals_map
  return locals_map
""", "<exec_function>", "exec"))

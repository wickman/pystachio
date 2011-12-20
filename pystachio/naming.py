import copy
from itertools import chain
import re

class Namable(object):
  class Unresolvable(Exception): pass

  def lookup(self, name):
    """Return whatever is named by 'name', or raise Namable.Unresolvable"""
    raise NotImplementedError

class Indexed(Namable):
  pass

class Dereferenced(Namable):
  pass


class Ref(object):
  """
    A reference into to a hierarchically named object.

    E.g. "foo" references the name foo.  The reference "foo.bar" references
    the name "bar" in foo's scope.  If foo is not a dictionary, this will
    result in an interpolation/binding error.
  """
  _REF_RE = re.compile('(\.\w+|\[\w+\])')
  _VALID_START = re.compile('[a-zA-Z_]')
  _COMPONENT_SEPARATOR = '.'

  class Component(object):
    def __init__(self, value):
      self._value = value

    @property
    def value(self):
      return self._value

  class Indexed(Component):
    RE = re.compile('^\w+$')
    def __repr__(self):
      return '[%s]' % self._value

  class Dereferenced(Component):
    RE = re.compile('^[a-zA-Z_]\w*$')
    def __repr__(self):
      return '.%s' % self._value

  class InvalidRefError(Exception): pass
  class UnnamableError(Exception): pass

  def __init__(self, address):
    if not (address.startswith('[') or address.startswith('.')):
      if Ref._VALID_START.match(address[0]):
        self._components = Ref.split_components('.' + address)
      else:
        raise Ref.InvalidRefError(address)
    else:
      self._components = Ref.split_components(address)

  def components(self):
    return self._components

  @staticmethod
  def split_components(address):
    def map_to_namable(component):
      if (component.startswith('[') and component.endswith(']') and
          Ref.Indexed.RE.match(component[1:-1])):
        return Ref.Indexed(component[1:-1])
      elif component.startswith('.') and Ref.Dereferenced.RE.match(component[1:]):
        return Ref.Dereferenced(component[1:])
      else:
        raise Ref.InvalidRefError('Address %s has bad component %s' % (address, component))
    splits = Ref._REF_RE.split(address)
    if any(splits[0::2]):
      raise Ref.InvalidRefError('Badly formed address %s' % address)
    splits = splits[1::2]
    return map(map_to_namable, splits)

  def address(self):
    joined = ''.join(map(str, self._components))
    if joined.startswith('.'):
      return joined[1:]
    else:
      return joined

  def __str__(self):
    return '{{%s}}' % self.address()

  def __repr__(self):
    return 'Ref(%s)' % self.address()

  def __eq__(self, other):
    return str(self) == str(other)

  def __hash__(self):
    return hash(str(self))

  def resolve(self, namable):
    """
      Resolve this Ref in the context of Namable namable.

      Raises Namable.Unresolvable on any miss.
    """
    for component in self.components():
      if isinstance(component, Ref.Indexed) and isinstance(namable, Indexed) or (
         isinstance(component, Ref.Dereferenced) and isinstance(namable, Dereferenced)):
        namable = namable.lookup(component.value)
      else:
        raise Ref.UnnamableError("Cannot resolve Ref %s from object: %s" % (
          component, repr(namable)))
    return namable

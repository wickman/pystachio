import re

from .compatibility import Compatibility


class frozendict(dict):
  """A hashable dictionary."""
  def __key(self):
    return tuple((k, self[k]) for k in sorted(self))

  def __hash__(self):
    return hash(self.__key())

  def __eq__(self, other):
    return self.__key() == other.__key()

  def __ne__(self, other):
    return self.__key() != other.__key()

  def __repr__(self):
    return 'frozendict(%s)' % dict.__repr__(self)


class Namable(object):
  """
    An object that can be named/dereferenced.
  """
  class Error(Exception): pass

  class Unnamable(Error):
    def __init__(self, obj):
      super(Namable.Unnamable, self).__init__('Object is not indexable: %s' %
          obj.__class__.__name__)

  class NamingError(Error):
    def __init__(self, obj, ref):
      super(Namable.NamingError, self).__init__('Cannot dereference object %s by %s' % (
          obj.__class__.__name__, ref.action()))

  class NotFound(Error):
    def __init__(self, obj, ref):
      super(Namable.NotFound, self).__init__('Could not find %s in object %s' % (ref.action().value,
        obj.__class__.__name__))

  def find(self, ref):
    """
      Given a ref, return the value referencing that ref.
      Raises Namable.NotFound if not found.
      Raises Namable.NamingError if try to dereference object in an invalid way.
      Raises Namable.Unnamable if try to dereference into an unnamable type.
    """
    raise NotImplementedError


class Ref(object):
  """
    A reference into to a hierarchically named object.
  """
  # ref re
  # ^[^\d\W]\w*\Z
  _DEREF_RE = r'[^\d\W]\w*'
  _INDEX_RE = r'[\w\-\./]+'
  _REF_RE = re.compile(r'(\.' + _DEREF_RE + r'|\[' + _INDEX_RE + r'\])')
  _VALID_START = re.compile(r'[a-zA-Z_]')
  _COMPONENT_SEPARATOR = '.'

  class Component(object):
    def __init__(self, value):
      self._value = value

    @property
    def value(self):
      return self._value

    def __hash__(self):
      return hash(self.value)

    def __eq__(self, other):
      return self.__class__ == other.__class__ and self.value == other.value

    def __ne__(self, other):
      return not (self == other)

    def __lt__(self, other):
      return self.value < other.value

    def __gt__(self, other):
      return self.value > other.value

  class Index(Component):
    RE = re.compile('^[\w\-\./]+$')

    def __repr__(self):
      return '[%s]' % self._value

  class Dereference(Component):
    RE = re.compile('^[^\d\W]\w*$')

    def __repr__(self):
      return '.%s' % self._value

  class InvalidRefError(Exception): pass
  class UnnamableError(Exception): pass

  @staticmethod
  def wrap(value):
    if isinstance(value, Ref):
      return value
    else:
      return Ref.from_address(value)

  @staticmethod
  def from_address(address):
    components = []
    if not address or not isinstance(address, Compatibility.stringy):
      raise Ref.InvalidRefError('Invalid address: %s' % repr(address))
    if not (address.startswith('[') or address.startswith('.')):
      if Ref._VALID_START.match(address[0]):
        components = Ref.split_components('.' + address)
      else:
        raise Ref.InvalidRefError(address)
    else:
      components = Ref.split_components(address)
    return Ref(components)

  def __init__(self, components):
    self._components = components

  def components(self):
    return self._components

  def action(self):
    return self._components[0]

  def is_index(self):
    return isinstance(self.action(), Ref.Index)

  def is_dereference(self):
    return isinstance(self.action(), Ref.Dereference)

  def is_empty(self):
    return len(self.components()) == 0

  def rest(self):
    return Ref(self.components()[1:])

  def __add__(self, other):
    sc = self.components()
    oc = other.components()
    return Ref(sc + oc)

  @staticmethod
  def subscope(ref1, ref2):
    rc = ref1.components()
    sc = ref2.components()
    if rc == sc[0:len(rc)]:
      if len(sc) > len(rc):
        return Ref(sc[len(rc):])

  def scoped_to(self, ref):
    return Ref.subscope(self, ref)

  @staticmethod
  def split_components(address):
    def map_to_namable(component):
      if (component.startswith('[') and component.endswith(']') and
          Ref.Index.RE.match(component[1:-1])):
        return Ref.Index(component[1:-1])
      elif component.startswith('.') and Ref.Dereference.RE.match(component[1:]):
        return Ref.Dereference(component[1:])
      else:
        raise Ref.InvalidRefError('Address %s has bad component %s' % (address, component))
    splits = Ref._REF_RE.split(address)
    if any(splits[0::2]):
      raise Ref.InvalidRefError('Badly formed address %s' % address)
    splits = splits[1::2]
    return [map_to_namable(spl) for spl in splits]

  def address(self):
    joined = ''.join(str(comp) for comp in self._components)
    if joined.startswith('.'):
      return joined[1:]
    else:
      return joined

  def __str__(self):
    return '{{%s}}' % self.address()

  def __repr__(self):
    return 'Ref(%s)' % self.address()

  def __eq__(self, other):
    return self.components() == other.components()

  def __ne__(self, other):
    return self.components() != other.components()

  @staticmethod
  def compare(self, other):
    if len(self.components()) < len(other.components()):
      return -1
    elif len(self.components()) > len(other.components()):
      return 1
    else:
      return (self.components() > other.components()) - (self.components() < other.components())

  def __lt__(self, other):
    return Ref.compare(self, other) == -1

  def __gt__(self, other):
    return Ref.compare(self, other) == 1

  def __hash__(self):
    return hash(str(self))

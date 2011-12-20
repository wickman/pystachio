import re

class Namable(object):
  """
    An object that exports a lookup() method for resolving names within that object.
  """
  class Unresolvable(Exception): pass

  def lookup(self, name):
    """Return whatever is named by 'name', or raise Namable.Unresolvable"""
    raise NotImplementedError

class Indexed(Namable):
  """
    An indexed object trait.
    (i.e. dereferenced via array-style access with '[]')
  """

class Dereferenced(Namable):
  """
    A dereferenced object trait.
    (i.e. dereferenced via '.'-style access with '.' like 'foo.bar')
  """

class Ref(object):
  """
    A reference into to a hierarchically named object.
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

    def __eq__(self, other):
      return self.__class__ == other.__class__ and self.value == other.value

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
    if not address or not isinstance(address, basestring):
      raise Ref.InvalidRefError('Invalid address: %s' % repr(address))
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
  def subscope(ref1, ref2):
    rc = ref1.components()
    sc = ref2.components()
    if rc == sc[0:len(rc)]:
      if len(sc) > len(rc):
        return sc[len(rc)]

  def scoped_to(self, ref):
    """
      Given a Ref :ref, return the immediate scoping action, or None if they
      do not share scopes.

      For example:
        Ref("a.b[c][d]").scoped_to(Ref("a.b")) => Ref.Indexed("c")
        Ref("a.b").scoped_to(Ref("a.b[c]")) => None
        Ref("a.b").scoped_to(Ref("a.b")) => None
        Ref("a.b.c").scoped_to(Ref("a.b")) => Ref.Dereferenced("c")
    """
    return Ref.subscope(self, ref)

  def scoped_in(self, ref):
    """
      Opposite of scoped_to.
    """
    return Ref.subscope(ref, self)

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

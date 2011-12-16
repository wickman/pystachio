import copy
import re

class ObjectId(object):
  """
    A reference to a hierarchically named object.

    E.g. "foo" references the name foo.  The reference "foo.bar" references
    the name "bar" in foo's scope.  If foo is not a dictionary, this will
    result in an interpolation/binding error.
  """

  _COMPONENT_RE = re.compile(r'^\w+$')
  _COMPONENT_SEPARATOR = '.'

  class InvalidObjectIdError(Exception): pass
  class UnboundObjectId(Exception): pass

  def __init__(self, address):
    self._address = address
    ObjectId.raise_if_invalid(self)

  def address(self):
    return self._address

  def components(self):
    return self._address.split(self._COMPONENT_SEPARATOR)

  @staticmethod
  def raise_if_invalid(oid):
    for component in oid.components():
      if not ObjectId._COMPONENT_RE.match(component):
        raise ObjectId.InvalidObjectIdError("Invalid address: %s at %s" % (
          oid.address(), component))

  def __str__(self):
    return '{{%s}}' % self._address

  def __repr__(self):
    return 'ObjectId(%s)' % self._address

  def __eq__(self, other):
    return self._address == other._address

  @staticmethod
  def interpolate(oid, oenv):
    for component in oid.components():
      if component not in oenv:
        raise ObjectId.UnboundObjectId("%s not in %s" % (component, oenv))
      else:
        oenv = oenv[component]
    return oenv

class ObjectMustacheParser(object):
  """
    Split strings on Mustache-style templates:
      a {{foo}} bar {{baz}} b => ['a ', ObjectId('foo'), ' bar ', ObjectId('baz'), ' b']

    To suppress parsing of individual tags, you can use {{&foo}} which emits '{{foo}}'
    instead of ObjectId('foo') or ObjectId('&foo').  As such, template variables cannot
    begin with '&'.
  """

  _ADDRESS_DELIMITER = '&'
  _MUSTACHE_RE = re.compile(r"{{(%c)?([^{}]+?)\1?}}" % _ADDRESS_DELIMITER)

  @staticmethod
  def split(string):
    splits = ObjectMustacheParser._MUSTACHE_RE.split(string)
    first_split = splits.pop(0)
    outsplits = [first_split] if first_split else []
    assert len(splits) % 3 == 0
    for k in range(0, len(splits), 3):
      if splits[k] == ObjectMustacheParser._ADDRESS_DELIMITER:
        outsplits.append('{{%s}}' % splits[k+1])
      elif splits[k] == None:
        outsplits.append(ObjectId(splits[k+1]))
      else:
        raise Exception("Unexpected parsing error in Mustache regular expression, splits[%s] = '%s'" % (
          k, splits[k]))
      if splits[k+2]:
        outsplits.append(splits[k+2])
    return outsplits

  @staticmethod
  def join(splits, environment, strict=True):
    """
      Interpolate strings.

      :params splits: Return the output of Parser.split(string)
      :params environment: The environment in which the interpolation should take place.
      :params strict (optional): If strict=True, raise an exception on unbounded variables.

      Returns 2-tuple containing:
        joined string, list of unbound object ids (potentially empty)
    """
    isplits = []
    uninterpolated = []
    for oid in splits:
      if isinstance(oid, ObjectId):
        try:
          interpolated = ObjectId.interpolate(oid, environment)
        except ObjectId.UnboundObjectId:
          interpolated = oid
          uninterpolated.append(oid)
          if strict:
            raise
        isplits.append(interpolated)
      else:
        isplits.append(oid)
    return (''.join(map(str, isplits)), uninterpolated)

class ObjectEnvironment(dict):
  """
    An attribute bundle that stores a dictionary of environment variables,
    supporting selective recursive merging.
  """

  def __init__(self, *dictionaries, **names):
    env = {}
    for d in dictionaries:
      ObjectEnvironment.merge(env, d)
    ObjectEnvironment.merge(env, names)
    dict.__init__(self, env)

  @staticmethod
  def merge(env1, env2):
    for key in env2:
      if key not in env1:
        env1[key] = env2[key]
      else:
        if isinstance(env1[key], dict) and isinstance(env2[key], dict):
          ObjectEnvironment.merge(env1[key], env2[key])
        else:
          env1[key] = env2[key]

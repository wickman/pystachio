import copy
import re

class ObjectId(object):
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

class ObjectEnvironment(dict):
  """
    Need an attribute bundle that works something like this:

      Stores {
        'daemon': {
          'id': 1234,
          'name': 'oh baby'
        },
        'mesos': {
          'datacenter': 'smf1-prod',
          'cluster': {
            'slaves': 1235,
            'executors': 1358,
            ...
          }
        }
      }

      Then attributes.update(mesos = { 'cluster': { 'nodes': 1325 } })
        => recursively dives down and replaces only leaves.

      Furthermore, needs to be able to
      scope1.merge(scope2).merge(scope3).evaluate(mustache expression)
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


from naming import Dereferenced

class Environment(dict, Dereferenced):
  """
    An attribute bundle that stores a dictionary of environment variables,
    supporting selective recursive merging.
  """

  def __init__(self, *dictionaries, **names):
    dict.__init__(self)
    for d in dictionaries:
      self.merge(d)
    self.merge(names)

  @staticmethod
  def wrap(value):
    if isinstance(value, dict):
      return Environment(value)
    else:
      return value

  def merge(self, d):
    for key in d:
      if key in self and isinstance(self[key], dict) and isinstance(d[key], dict):
        self[key].merge(d[key])
      else:
        self[key] = Environment.wrap(d[key])

  def lookup(self, name):
    if name in self:
      return self[name]
    else:
      raise Dereferenced.Unresolvable(name)

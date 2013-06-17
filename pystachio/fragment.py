import json

from .compatibility import Compatibility


class Fragment(object):
  @classmethod
  def compatible(cls, fragments):
    if len(fragments) == 0:
      return True
    return all(isinstance(fragment, fragments[0].__class__) for fragment in fragments)

  @classmethod
  def join(cls, fragments):
    raise NotImplementedError
    
  def __init__(self, value):
    self.value = value


class StringFragment(Fragment):
  @classmethod
  def join(cls, fragments):
    if not cls.compatible(fragments):
      raise TypeError('Mustache fragments have incompatible types.')
    return ''.join(fragment.value for fragment in fragments)
  
  def __init__(self, value):
    super(StringFragment, self).__init__((str if Compatibility.PY3 else unicode)(value))

  def __repr__(self):
    return '%s(%r)' % (self.__class__.__name__, self.value)


class JsonFragment(Fragment):
  @classmethod
  def join(cls, fragments):
    if not isinstance(fragments, cls):
      raise TypeError('JsonFragment can only deserialize json fragments.')
    if len(fragments) != 1:
      raise ValueError('Can only join a single json fragment at a time.')
    return json.loads(fragments[0].value)

  def __init__(self, value): 
    super(JsonFragment, self).__init__(json.dumps(value))
import re

from .compatibility import Compatibility
from .naming import Namable, Ref


class MustacheParser(object):
  """
    Split strings on Mustache-style templates:
      a {{foo}} bar {{baz}} b => ['a ', Ref('foo'), ' bar ', Ref('baz'), ' b']

    To suppress parsing of individual tags, you can use {{&foo}} which emits '{{foo}}'
    instead of Ref('foo') or Ref('&foo').  As such, template variables cannot
    begin with '&'.
  """

  ADDRESS_DELIMITER = '&'
  MUSTACHE_RE = re.compile(r"{{(%c)?([^{}]+?)\1?}}" % ADDRESS_DELIMITER)
  MAX_ITERATIONS = 100

  class Error(Exception): pass
  class Uninterpolatable(Error): pass

  @classmethod
  def merge(cls, array):
    pos = 0
    while pos < len(array) - 1:
      if isinstance(array[pos], Ref) or isinstance(array[pos + 1], Ref):
        pos += 1
        continue
      array = array[:pos] + [''.join(array[pos:pos + 2])] + array[pos + 2:]
    return array

  @classmethod
  def split(cls, string, downcast=False):
    """
      Split a string into a sequence of (str, ref, str, ref, ...)
      If downcast=True, translate {{&references}} into {{references}}.
    """
    splits = cls.MUSTACHE_RE.split(string)
    first_split = splits.pop(0)
    outsplits = [first_split] if first_split else []
    assert len(splits) % 3 == 0
    for k in range(0, len(splits), 3):
      if splits[k] == cls.ADDRESS_DELIMITER:
        outsplits.append('{{%s%s}}' % ('' if downcast else cls.ADDRESS_DELIMITER, splits[k + 1]))
      elif splits[k] == None:
        outsplits.append(Ref.from_address(splits[k + 1]))
      else:
        raise cls.Error("Unexpected parsing error in Mustache: splits[%s] = '%s'" % (k, splits[k]))
      if splits[k + 2]:
        outsplits.append(splits[k + 2])
    return cls.merge(outsplits)

  @staticmethod
  def join(splits, *namables):
    """
      Interpolate strings.

      :params splits: The output of MustacheParser.split(string)
      :params namables: A sequence of Namable objects in which the interpolation should take place.

      Returns 2-tuple containing:
        joined string, list of unbound object ids (potentially empty)
    """
    isplits = []
    unbound = []
    for ref in splits:
      if not isinstance(ref, Ref):
        isplits.append(ref)
        continue
      for namable in namables:
        try:
          value = namable.find(ref)
        except Namable.Error as e:
          continue
        isplits.append(value)
        break
      else:
        isplits.append(ref)
        unbound.append(ref)
    return (''.join(map(str if Compatibility.PY3 else unicode, isplits)), unbound)

  @classmethod
  def resolve(cls, stream, *namables):
    def iterate(st, downcast=False):
      refs = MustacheParser.split(st, downcast)
      unbound = [ref for ref in refs if isinstance(ref, Ref)]
      repl, interps = MustacheParser.join(refs, *namables)
      rebound = [ref for ref in MustacheParser.split(repl, downcast) if isinstance(ref, Ref)]
      return repl, interps, unbound
    iterations = 0
    for iteration in range(cls.MAX_ITERATIONS):
      stream, interps, unbound = iterate(stream)
      if interps == unbound:
        break
    else:
      raise cls.Uninterpolatable('Unable to interpolate %s!  Maximum replacements reached.'
          % stream)
    stream, _, unbound = iterate(stream, downcast=True)
    return stream, unbound

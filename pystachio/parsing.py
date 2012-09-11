import re

from pystachio.compatibility import Compatibility
from pystachio.naming import Namable, Ref

class MustacheParser(object):
  """
    Split strings on Mustache-style templates:
      a {{foo}} bar {{baz}} b => ['a ', Ref('foo'), ' bar ', Ref('baz'), ' b']

    To suppress parsing of individual tags, you can use {{&foo}} which emits '{{foo}}'
    instead of Ref('foo') or Ref('&foo').  As such, template variables cannot
    begin with '&'.
  """

  _ADDRESS_DELIMITER = '&'
  _MUSTACHE_RE = re.compile(r"{{(%c)?([^{}]+?)\1?}}" % _ADDRESS_DELIMITER)
  MAX_ITERATIONS = 100

  class Error(Exception): pass
  class Uninterpolatable(Error): pass

  @staticmethod
  def split(string, keep_aliases=False):
    splits = MustacheParser._MUSTACHE_RE.split(string)
    first_split = splits.pop(0)
    outsplits = [first_split] if first_split else []
    assert len(splits) % 3 == 0
    for k in range(0, len(splits), 3):
      if splits[k] == MustacheParser._ADDRESS_DELIMITER:
        outsplits.append('{{%s%s}}' % (
            MustacheParser._ADDRESS_DELIMITER if keep_aliases else '',
            splits[k+1]))
      elif splits[k] == None:
        outsplits.append(Ref.from_address(splits[k+1]))
      else:
        raise Exception("Unexpected parsing error in Mustache: splits[%s] = '%s'" % (
          k, splits[k]))
      if splits[k+2]:
        outsplits.append(splits[k+2])
    return outsplits

  @staticmethod
  def join(splits, *namables):
    """
      Interpolate strings.

      :params splits: The output of Parser.split(string)
      :params namables: A sequence of Namable objects in which the interpolation should take place.

      Returns 2-tuple containing:
        joined string, list of unbound object ids (potentially empty)
    """
    isplits = []
    unbound = []
    for ref in splits:
      if isinstance(ref, Ref):
        resolved = False
        for namable in namables:
          try:
            value = namable.find(ref)
            resolved = True
            break
          except Namable.Error as e:
            continue
        if resolved:
          isplits.append(value)
        else:
          isplits.append(ref)
          unbound.append(ref)
      else:
        isplits.append(ref)
    return (''.join(map(str if Compatibility.PY3 else unicode, isplits)), unbound)

  @classmethod
  def resolve(cls, stream, *namables):
    def iterate(st, keep_aliases=True):
      refs = MustacheParser.split(st, keep_aliases=keep_aliases)
      unbound = [ref for ref in refs if isinstance(ref, Ref)]
      repl, interps = MustacheParser.join(refs, *namables)
      rebound = [ref for ref in MustacheParser.split(repl, keep_aliases=keep_aliases)
                 if isinstance(ref, Ref)]
      return repl, interps, unbound

    iterations = 0
    for iteration in range(cls.MAX_ITERATIONS):
      stream, interps, unbound = iterate(stream, keep_aliases=True)
      if interps == unbound:
        break
    else:
      raise cls.Uninterpolatable('Unable to interpolate %s!  Maximum replacements reached.'
          % stream)

    stream, _, unbound = iterate(stream, keep_aliases=False)
    return stream, unbound

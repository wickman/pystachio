import re

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

  class Uninterpolatable(Exception): pass

  @staticmethod
  def split(string):
    splits = MustacheParser._MUSTACHE_RE.split(string)
    first_split = splits.pop(0)
    outsplits = [first_split] if first_split else []
    assert len(splits) % 3 == 0
    for k in range(0, len(splits), 3):
      if splits[k] == MustacheParser._ADDRESS_DELIMITER:
        outsplits.append('{{%s}}' % splits[k+1])
      elif splits[k] == None:
        outsplits.append(Ref.from_address(splits[k+1]))
      else:
        raise Exception("Unexpected parsing error in Mustache: splits[%s] = '%s'" % (
          k, splits[k]))
      if splits[k+2]:
        outsplits.append(splits[k+2])
    return outsplits

  @staticmethod
  def join(splits, *namables, **kw):
    """
      Interpolate strings.

      :params splits: Return the output of Parser.split(string)
      :params namables: A sequence of Namable objects in which the interpolation should take place.
      :kwargs "strict" (optional, defaults to True): If strict=True, raise an exception on unbound
        variables.

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
            # value = ref.resolve(namable)
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
          if kw.get('strict', True):
            raise MustacheParser.Uninterpolatable(ref.address())
      else:
        isplits.append(ref)
    return (''.join(map(unicode, isplits)), unbound)

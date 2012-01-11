import pytest
from pystachio.naming import Ref, Namable
from pystachio.basic import *
from pystachio.container import List, Map
from pystachio.composite import Struct

def ref(address):
  return Ref.from_address(address)

def test_basic_lists():
  assert List(Integer)([]).check().ok()
  assert List(Integer)([1]).check().ok()
  assert List(Integer)((1,)).check().ok()
  assert List(Integer)(["1",]).check().ok()
  assert not List(Integer)([1, "{{two}}"]).check().ok()
  assert (List(Integer)([1, "{{two}}"]) % {'two': 2}).check().ok()
  with pytest.raises(ValueError):
    List(Integer)({'not': 'a', 'list': 'type'})
  repr(List(Integer)([1, '{{two}}']))

def test_basic_scoping():
  i = Integer('{{intvalue}}')
  lst = List(Integer)([i.bind(intvalue = 1), i.bind(intvalue = 2), i])
  lsti, _ = lst.bind(intvalue = 3).interpolate()
  assert lsti == List(Integer)([Integer(1), Integer(2), Integer(3)])
  lsti, _ = lst.in_scope(intvalue = 3).interpolate()
  assert lsti == List(Integer)([Integer(1), Integer(2), Integer(3)])
  one = ref('[0]')
  two = ref('[1]')
  three = ref('[2]')
  assert lst.find(one) == Integer(1)
  assert lst.find(two) == Integer(2)
  assert lst.find(three) == Integer('{{intvalue}}')
  assert lst.in_scope(intvalue = 3).find(one) == Integer(1)
  assert lst.in_scope(intvalue = 3).find(two) == Integer(2)
  assert lst.in_scope(intvalue = 3).find(three) == Integer(3)

def test_iteration():
  li = List(Integer)([1,2,3])
  liter = iter(li)
  assert next(liter) == Integer(1)
  assert next(liter) == Integer(2)
  assert next(liter) == Integer(3)
  with pytest.raises(StopIteration):
    next(liter)
  li = List(Integer)([])
  with pytest.raises(StopIteration):
    next(iter(li))

def test_indexing():
  li = List(Integer)([1,2,3])
  for bad in ['a', None, type, Integer]:
    with pytest.raises(TypeError):
      li[bad]

  # Indexing should also support slices
  li = List(Integer)(range(10))
  assert li[0] == Integer(0)
  assert li[-1] == Integer(9)
  assert li[::2] == (Integer(0), Integer(2), Integer(4), Integer(6), Integer(8))
  assert li[8:] == (Integer(8), Integer(9))
  assert li[2:0:-1] == (Integer(2), Integer(1))
  with pytest.raises(IndexError):
    li[10]

def test_list_scoping():
  assert List(Integer)([1, "{{wut}}"]).interpolate() == (
    List(Integer)([Integer(1), Integer('{{wut}}')]), [ref('wut')])
  assert List(Integer)([1, "{{wut}}"]).bind(wut = 23).interpolate() == (
    List(Integer)([Integer(1), Integer(23)]), [])
  assert List(Integer)([1, Integer("{{wut}}").bind(wut = 24)]).bind(wut = 23).interpolate() == (
    List(Integer)([Integer(1), Integer(24)]), [])

def test_list_find():
  ls = List(String)(['a', 'b', 'c'])
  assert ls.find(ref('[0]')) == String('a')
  with pytest.raises(Namable.NamingError):
    ls.find(ref('.a'))
  with pytest.raises(Namable.NamingError):
    ls.find(ref('[a]'))
  with pytest.raises(Namable.NotFound):
    ls.find(ref('[4]'))
  with pytest.raises(Namable.Unnamable):
    ls.find(ref('[1].foo'))

def test_list_provides():
  assert List(String).provides(ref('[0]'))
  assert not List(String).provides(ref('[0].unprovided'))
  class Employee(Struct):
    first = String
    last = String
  assert List(Employee).provides(ref('[0].first'))
  assert not List(Employee).provides(ref('[0].unknown_field'))
  assert List(Map(String,String)).provides(ref('[0]'))
  assert List(Map(String,String)).provides(ref('[0][foo]'))
  assert not List(Map(String,String)).provides(ref('[0].foo'))
  # TODO(wickman) Do basic coercion checks so that
  # assert not List(String).provides(ref('[invalid]'))

def test_equals():
  assert List(Integer)([1, "{{wut}}"]).bind(wut=23) == List(Integer)([1, 23])

def test_basic_maps():
  assert Map(String,Integer)({}).check().ok()
  assert Map(String,Integer)({'a':1}).check().ok()
  assert Map(String,Integer)(('a', 1)).check().ok()
  assert Map(String,Integer)(('a', 1), ('b', 2)).check().ok()
  assert not Map(String,Integer)({'a':'{{foo}}'}).check().ok()
  assert not Map(Integer,String)({'{{foo}}':'a'}).check().ok()
  assert Map(String,Integer)({'a':'{{foo}}'}).bind(foo = 5).check().ok()
  with pytest.raises(TypeError):
    Map(String,Integer)(a = 1)
  with pytest.raises(ValueError):
    Map(String,Integer)({'a': 1}, {'b': 2})
  for value in [None, type, 123, 'a']:
    with pytest.raises(ValueError):
      Map(String,Integer)(value)
  repr(Map(String,Integer)(('a', 1), ('b', 2)))

def test_map_find():
  msi = Map(String,Integer)({'a':1})
  assert msi.find(ref('[a]')) == Integer(1)
  with pytest.raises(Namable.NamingError):
    msi.find(ref('.a'))
  with pytest.raises(Namable.NotFound):
    msi.find(ref('[b]'))
  with pytest.raises(Namable.Unnamable):
    msi.find(ref('[a].foo'))

  mii = Map(Integer,String)({3: 'foo', '5': 'bar'})
  assert mii.find(ref('[3]')) == String('foo')
  assert mii.find(ref('[5]')) == String('bar')

def test_map_provides():
  assert Map(String, Integer).provides(ref('[foo]'))
  assert not Map(String, Integer).provides(ref('[0].unprovided'))
  class Employee(Struct):
    first = String
    last = String
  assert Map(Integer,Employee).provides(ref('[0].first'))
  assert not Map(Integer,Employee).provides(ref('[0].unknown_field'))
  assert Map(String,List(String)).provides(ref('[0]'))
  assert Map(String,List(String)).provides(ref('[bar][foo]'))
  assert not Map(String,List(String)).provides(ref('[0].foo'))

def test_map_iteration():
  mi = Map(String,Integer)({'a': 1, 'b': 2})
  miter = iter(mi)
  assert next(miter) == String('a')
  assert next(miter) == String('b')
  with pytest.raises(StopIteration):
    next(miter)

  mi = Map(String,Integer)({})
  with pytest.raises(StopIteration):
    next(iter(mi))

def test_map_indexing():
  mi = Map(String,Integer)({'a': 1, 'b': 2})
  assert mi['a'] == Integer(1)
  assert mi[String('b')] == Integer(2)
  for key in ['c', String('c')]:
    with pytest.raises(KeyError):
      mi[key]

@pytest.mark.xfail(reason="Need to improve pre-coercion for basic types.")
def test_bad_map_indexing():
  mi = Map(String,Integer)({'a': 1, 'b': 2})
  for key in [String, Integer, Integer(1), 1, None, type]:
    with pytest.raises(TypeError):
      mi[key]

def test_hashing():
  map = {
    List(Integer)([1,2,3]): 'foo',
    Map(String,Integer)({'a': 1, 'b': 2}): 'bar'
  }
  assert List(Integer)([1,2,3]) in map
  assert Map(String,Integer)({'a': 1, 'b': 2}) in map
  assert List(Integer)([3,2,1]) not in map
  assert Map(String,Integer)({'b': 2, 'a': 1}) in map
  assert Map(String,Integer)({'a': 2, 'b': 1}) not in map

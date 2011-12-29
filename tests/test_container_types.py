import pytest
from pystachio.naming import Ref, Namable
from pystachio.basic import *
from pystachio.container import List, Map

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

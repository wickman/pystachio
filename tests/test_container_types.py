from pystachio.naming import Ref
from pystachio.basic import *
from pystachio.container import List, Map

def test_basic_lists():
  assert List(Integer)([]).check().ok()
  assert List(Integer)([1]).check().ok()
  assert List(Integer)((1,)).check().ok()
  assert List(Integer)(["1",]).check().ok()
  assert not List(Integer)([1, "{{two}}"]).check().ok()
  assert (List(Integer)([1, "{{two}}"]) % {'two': 2}).check().ok()

def test_basic_scoping():
  i = Integer('{{intvalue}}')
  lst = List(Integer)([i.bind(intvalue = 1), i.bind(intvalue = 2), i])
  lsti, _ = lst.bind(intvalue = 3).interpolate()
  assert lsti == List(Integer)([Integer(1), Integer(2), Integer(3)])
  lsti, _ = lst.in_scope(intvalue = 3).interpolate()
  assert lsti == List(Integer)([Integer(1), Integer(2), Integer(3)])
  one = Ref.from_address('[0]')
  two = Ref.from_address('[1]')
  three = Ref.from_address('[2]')
  assert lst.find(one) == Integer(1)
  assert lst.find(two) == Integer(2)
  assert lst.find(three) == Integer('{{intvalue}}')
  assert lst.in_scope(intvalue = 3).find(one) == Integer(1)
  assert lst.in_scope(intvalue = 3).find(two) == Integer(2)
  assert lst.in_scope(intvalue = 3).find(three) == Integer(3)

def test_list_scoping():
  assert List(Integer)([1, "{{wut}}"]).interpolate() == (
    List(Integer)([Integer(1), Integer('{{wut}}')]), [Ref.from_address('wut')])
  assert List(Integer)([1, "{{wut}}"]).bind(wut = 23).interpolate() == (
    List(Integer)([Integer(1), Integer(23)]), [])
  assert List(Integer)([1, Integer("{{wut}}").bind(wut = 24)]).bind(wut = 23).interpolate() == (
    List(Integer)([Integer(1), Integer(24)]), [])

def test_equals():
  assert List(Integer)([1, "{{wut}}"]).bind(wut=23) == List(Integer)([1, 23])

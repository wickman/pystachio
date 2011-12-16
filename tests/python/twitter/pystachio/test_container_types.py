import pytest
import unittest
from twitter.pystachio import (
  ObjectId,
  String,
  Integer,
  Float,
  Map,
  List)

def test_basic_lists():
  assert List(Integer)([]).check().ok()
  assert List(Integer)([1]).check().ok()
  assert List(Integer)((1,)).check().ok()
  assert not List(Integer)(["1",]).check().ok()
  assert not List(Integer)(["1",1]).check().ok()

def test_list_scoping():
  assert List(Integer)([1, "{{wut}}"]).interpolate() == (List(Integer)([Integer(1), Integer('{{wut}}')]),
    [ObjectId('wut')])
  assert List(Integer)([1, "{{wut}}"]).bind(wut = 23).interpolate() == (
    List(Integer)([Integer(1), Integer(23)]), [])
  assert List(Integer)([1, Integer("{{wut}}").bind(wut = 24)]).bind(wut = 23).interpolate() == (
    List(Integer)([Integer(1), Integer(24)]), [])

def test_equals():
  assert List(Integer)([1, "{{wut}}"]).bind(wut=23) == List(Integer)([1, 23])


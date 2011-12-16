import pytest
import unittest
from twitter.pystachio import (
  Empty,
  String,
  Integer,
  Float,
  Map,
  List,
  Composite,
  Default,
  Required)

def test_basic_types():
  class Resources(Composite):
    cpu = Float
    ram = Integer
  assert Resources().check().ok()
  assert Resources(cpu = 1.0).check().ok()
  assert Resources(cpu = 1.0, ram = 100).check().ok()
  assert not Resources(cpu = 1, ram = 100).check().ok()

def test_nested_composites():
  class Resources(Composite):
    cpu = Float
    ram = Integer
  class Process(Composite):
    name = String
    resources = Resources
  assert Process().check().ok()
  assert Process(name = "hello_world").check().ok()
  assert Process(resources = Resources()).check().ok()
  assert Process(resources = Resources(cpu = 1.0)).check().ok()
  assert not Process(resources = Resources(cpu = 1)).check().ok()
  assert not Process(name = 15)(resources = Resources(cpu = 1.0)).check().ok()


def test_defaults():
  class Resources(Composite):
    cpu = Default(Float, 1.0)
    ram = Integer
  assert Resources()._schema_data['cpu'] == Float(1.0)
  assert Resources(cpu = 2.0)._schema_data['cpu'] == Float(2.0)

  class Process(Composite):
    name = String
    resources = Default(Resources, Resources(cpu = 1.0))

  assert Process().check().ok()
  assert Process()(resources = Empty).check().ok()

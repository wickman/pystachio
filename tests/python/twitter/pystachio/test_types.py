import pytest
import unittest
from twitter.pystachio import (
  String,
  Integer,
  Float,
  Map,
  List,
  Composite)

def test_basic_types():
  class Resources(Composite):
    cpu = Float(required=True)
    ram = Integer(required=True)
    disk = Integer

  class Process(Composite):
    name = String(required=True)
    min_resources = Resources
    max_resources = Resources(required=True)

  # conflation of instance and type .. need a metaclass to build a concrete type annotated
  # with the attributes.  basically Int(required=True,default=23) is RequiredIntDefault23 type
  # that .checks(), .coerce() etc differently.
  #
  # the challenge syntactically is to get Int.check(...) to behave as if required=False,default=Empty
  # 
  # it's like a metaclass that behaves in the fashion of the _objects_ that we're constructing!
  # neat.  so like p(name = "hello").name() => "hello" but p().name() => the default
  #
  # similarly, Int is a type, but we want Int(required=False) to also be a type.
  # can we override a __call__ method in a metaclass?  whoa.
  r = Resources()

  assert r.check(
    Resources(cpu = 1.0, disk = 1000)) is False, "Missing ram which is required"
  assert r.check(Resources(cpu = 1.0, ram = 1000))

  r = Resources(cpu = 1.0, disk = 1000)
  p = Process()  
  assert p.check(Process(name = "hello_world", min_resources = r)) is False, (
    "min_resources is missing ram and should not type check.")
  assert p.check(Process(name = "hello_world", max_resources = r)) is False
  assert p.check(Process(name = "hello_world", max_resources = r(ram=10)))
  

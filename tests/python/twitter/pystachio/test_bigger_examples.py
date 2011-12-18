import pytest
import unittest

from twitter.pystachio import *

class CommandLine(Composite):
  binary = Required(String)
  args   = List(String)
  params = Map(String, String)

class Resources(Composite):
  cpu  = Required(Float)
  ram  = Required(Integer)
  disk = Default(Integer, 2 * 2**30)

class Process(Composite):
  name         = Required(String)
  resources    = Required(Resources)
  cmdline      = String
  command      = CommandLine
  max_failures = Default(Integer, 1)

class Task(Composite):
  name         = Required(String)
  processes    = Required(List(Process))
  max_failures = Default(Integer, 1)

def test_simple_task():
  command = "echo I am {{process.name}} in {{mesos.datacenter}}."
  process_template = Process(
    name = '{{process.name}}',
    resources = Resources(cpu = 1.0, ram = 2**24),
    cmdline = command)
  basic = Task(name = "basic")(
    processes = [
      process_template.bind(process = {'name': 'process_1'}),
      process_template.bind(process = {'name': 'process_2'}),
      process_template.bind(process = {'name': 'process_3'}),
    ])

  bi, unbound = basic.interpolate()
  assert unbound == [Ref('mesos.datacenter')]

  bi, unbound = (basic % {'mesos': {'datacenter': 'california'}}).interpolate()
  assert unbound == []
  assert bi.check().ok()

def test_type_type_type():
  ages = Map(String,Integer)({
    'brian': 30,
    'robey': 5000,
    'ian': 15
  })

  wtf = Map(Map(String, Integer), Float)({
    ages: 1.0
  })

  assert Map(String,Integer) == Map(String,Integer)
  assert isinstance(Map(String,Integer)({}), Map(String,Integer))
  assert isinstance(Map(Map(String,Integer),Integer)({}), Map(Map(String,Integer),Integer))

def test_recursive_unwrapping():
  task = {
    'name': 'basic',
    'processes': [
      {
        'name': 'process1',
        'resources': {
           'cpu': 1.0,
           'ram': 100},
        'cmdline': 'echo hello world'
      }
    ]
  }
  assert Task(**task).check().ok()
  assert Task(task).check().ok()
  assert Task(task, **task).check().ok()

  task['processes'][0].pop('name')
  assert not Task(task).check().ok()
  assert not Task(**task).check().ok()
  assert not Task(task, **task).check().ok()

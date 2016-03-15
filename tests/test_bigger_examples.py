from pystachio import *


class CommandLine(Struct):
  binary = Required(String)
  args   = List(String)
  params = Map(String, String)

class Resources(Struct):
  cpu  = Required(Float)
  ram  = Required(Integer)
  disk = Default(Integer, 2 * 2**30)

class Process(Struct):
  name         = Required(String)
  resources    = Required(Resources)
  cmdline      = String
  command      = CommandLine
  max_failures = Default(Integer, 1)

class Task(Struct):
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
  assert unbound == [Ref.from_address('mesos.datacenter')]

  bi, unbound = (basic % {'mesos': {'datacenter': 'california'}}).interpolate()
  assert unbound == []
  assert bi.check().ok()

def test_type_type_type():
  assert Map(String,Integer) != Map(String,Integer), "Types are no longer memoized."
  assert isinstance(Map(String,Integer)({}), Map(String,Integer))
  assert isinstance(Map(Map(String,Integer),Integer)({}), Map(Map(String,Integer),Integer))

  fake_ages = Map(String,Integer)({
    'brian': 28,
    'robey': 5000,
    'ian': 15
  })

  real_ages = Map(String,Integer)({
    'brian': 30,
    'robey': 37,
    'ian': 21
  })

  believability = Map(Map(String, Integer), Integer)({
    fake_ages: 0,
    real_ages: 1
  })

  assert Map(Map(String, Integer), Integer)(believability.get()) == believability


def test_recursive_unwrapping():
  task = {
    'name': 'basic',
    'processes': [
      {
        'name': 'process1',
        'resources': {
           'cpu': 1.0,
           'ram': 100
         },
        'cmdline': 'echo hello world'
      }
    ]
  }
  assert Task(**task).check().ok()
  assert Task(task).check().ok()
  assert Task(task, **task).check().ok()
  assert Task(task) == Task(Task(task).get())

  task['processes'][0].pop('name')
  assert not Task(task).check().ok()
  assert not Task(**task).check().ok()
  assert not Task(task, **task).check().ok()
  assert Task(task) == Task(Task(task).get())

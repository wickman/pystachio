# Pystachio #
[![Build Status](https://travis-ci.org/wickman/pystachio.svg)](https://travis-ci.org/wickman/pystachio)

### tl;dr ###

Pystachio is a type-checked dictionary templating library.

### why? ###

Its primary use is for the construction of miniature domain-specific
configuration languages.  Schemas defined by Pystachio can themselves be
serialized and reconstructed into other Python interpreters.  Pystachio
objects are tailored via Mustache templates, as explained in the section on
templating.

## Similar projects ##

This project is unrelated to the defunct Javascript Python interpreter.

Notable related projects:

* [dictshield](http://github.com/j2labs/dictshield)
* [remoteobjects](http://github.com/saymedia/remoteobjects)
* Django's [model.Model](https://docs.djangoproject.com/en/dev/ref/models/instances/)

## Requirements ##

Tested and works in CPython3 and PyPy3.

## Overview ##

You can define a structured type through the 'Struct' type:

    from pystachio import (
      Integer,
      String,
      Struct)

    class Employee(Struct):
      first = String
      last  = String
      age   = Integer


By default all fields are optional:

    >>> Employee().check()
    TypeCheck(OK)

    >>> Employee(first = 'brian')
    Employee(first=brian)
    >>> Employee(first = 'brian').check()
    TypeCheck(OK)


But it is possible to make certain fields required:

    from pystachio import Required

    class Employee(Struct):
      first = Required(String)
      last  = Required(String)
      age   = Integer

We can still instantiate objects with empty fields:

    >>> Employee()
    Employee()


But they will fail type checks:

    >>> Employee().check()
    TypeCheck(FAILED): Employee[last] is required.


Struct objects are purely functional and hence immutable after
constructed, however they are composable like functors:

    >>> brian = Employee(first = 'brian')
    >>> brian(last = 'wickman')
    Employee(last=wickman, first=brian)
    >>> brian
    Employee(first=brian)
    >>> brian = brian(last='wickman')
    >>> brian.check()
    TypeCheck(OK)


Object fields may also acquire defaults:

    class Employee(Struct):
      first    = Required(String)
      last     = Required(String)
      age      = Integer
      location = Default(String, "San Francisco")

    >>> Employee()
    Employee(location=San Francisco)


Schemas wouldn't be terribly useful without the ability to be hierarchical:

    class Location(Struct):
      city = String
      state = String
      country = String

    class Employee(Struct):
      first    = Required(String)
      last     = Required(String)
      age      = Integer
      location = Default(Location, Location(city = "San Francisco"))

    >>> Employee(first="brian", last="wickman")
    Employee(last=wickman, location=Location(city=San Francisco), first=brian)

    >>> Employee(first="brian", last="wickman").check()
    TypeCheck(OK)


## The type system ##

There are five basic types, two basic container types and then the `Struct` and `Choice` types.

### Basic Types ###

There are five basic types: `String`, `Integer`, `Float`, `Boolean` and `Enum`.  The first four behave as expected:

    >>> Float(1.0).check()
    TypeCheck(OK)
    >>> String("1.0").check()
    TypeCheck(OK)
    >>> Integer(1).check()
    TypeCheck(OK)
    >>> Boolean(False).check()
    TypeCheck(OK)

They also make a best effort to coerce into the appropriate type:

    >>> Float("1.0")
    Float(1.0)
    >>> String(1.0)
    String(1.0)
    >>> Integer("1")
    Integer(1)
    >>> Boolean("true")
    Boolean(True)

Though the same gotchas apply as standard coercion in Python:

    >>> int("1.0")
    ValueError: invalid literal for int() with base 10: '1.0'
    >>> Integer("1.0")
    pystachio.objects.CoercionError: Cannot coerce '1.0' to Integer

with the exception of `Boolean` which accepts "false" as falsy.


Enum is a factory that produces new enumeration types:

    >>> Enum('Red', 'Green', 'Blue')
    <class 'pystachio.typing.Enum_Red_Green_Blue'>
    >>> Color = Enum('Red', 'Green', 'Blue')
    >>> Color('Red')
    Enum_Red_Green_Blue(Red)
    >>> Color('Brown')
    Traceback (most recent call last):
      File "<console>", line 1, in <module>
      File "/Users/wickman/clients/pystachio/pystachio/basic.py", line 208, in __init__
        self.__class__.__name__, ', '.join(self.VALUES)))
    ValueError: Enum_Red_Green_Blue only accepts the following values: Red, Green, Blue

Enums can also be constructed using `namedtuple` syntax to generate more illustrative class names:

    >>> Enum('Color', ('Red', 'Green', 'Blue'))
    <class 'pystachio.typing.Color'>
    >>> Color = Enum('Color', ('Red', 'Green', 'Blue'))
    >>> Color('Red')
    Color(Red)


### Choices  ####

Choice types represent alternatives - values that can have one of some set of values.

    >>> C = Choice([Integer, String])
    >>> c1 = C("abc")
    >>> c2 = C(343)
    
### Container types ###

There are two container types: the `List` type and the `Map` type.  Lists
are parameterized by the type they contain, and Maps are parameterized from
a key type to a value type.

#### Lists ####

You construct a `List` by specifying its type (it actually behaves like a
metaclass, since it produces a type):

    >>> List(String)
    <class 'pystachio.container.StringList'>
    >>> List(String)([])
    StringList()
    >>> List(String)(["a", "b", "c"])
    StringList(a, b, c)


They compose like expected:

    >>> li = List(Integer)
    >>> li
    <class 'pystachio.container.IntegerList'>
    >>> List(li)
    <class 'pystachio.container.IntegerListList'>
    >>> List(li)([li([1,"2",3]), li([' 2', '3 ', 4])])
    IntegerListList(IntegerList(1, 2, 3), IntegerList(2, 3, 4))


Type checking is done recursively:

    >> List(li)([li([1,"2",3]), li([' 2', '3 ', 4])]).check()
    TypeCheck(OK)


#### Maps ####

You construct a `Map` by specifying the source and destination types:

    >>> ages = Map(String, Integer)({
    ...   'brian': 30,
    ...   'ian': 15,
    ...   'robey': 5000
    ... })
    >>> ages
    StringIntegerMap(brian => 28, ian => 15, robey => 5000)
    >>> ages.check()
    TypeCheck(OK)

Much like all other types, these types are immutable.  The only way to
"mutate" would be to create a whole new Map.  Technically speaking these
types are hashable as well, so you can construct stranger composite types
(added indentation for clarity.)

    >>> fake_ages = Map(String, Integer)({
    ...   'brian': 28,
    ...   'ian': 15,
    ...   'robey': 5000
    ... })
    >>> real_ages = Map(String, Integer)({
    ...   'brian': 30,
    ...   'ian': 21,
    ...   'robey': 35
    ... })
    >>> believability = Map(Map(String, Integer), Float)({
    ...   fake_ages: 0.2,
    ...   real_ages: 0.9
    ... })
    >>> believability
    StringIntegerMapFloatMap(
      StringIntegerMap(brian => 28, ian => 15, robey => 5000) => 0.2,
      StringIntegerMap(brian => 30, ian => 21, robey => 35) => 0.9)

    

## Object scopes ##

Objects have "environments": a set of bound scopes that follow the Object
around.  Objects are still immutable.  The act of binding a variable to an
Object just creates a new object with an additional variable scope.  You can
print the scopes by using the `scopes` function:

    >>> String("hello").scopes()
    ()

You can bind variables to that object with the `bind` function:

    >>> String("hello").bind(herp = "derp")
    String(hello)

The environment variables of an object do not alter equality, for example:

    >>> String("hello") == String("hello")
    True
    >>> String("hello").bind(foo = "bar") == String("hello")
    True

The object appears to be the same but it carries that scope around with it:

    >>> String("hello").bind(herp = "derp").scopes()
    (Environment({Ref(herp): 'derp'}),)


Furthermore you can bind multiple times:

    >>> String("hello").bind(herp = "derp").bind(herp = "extra derp").scopes()
    (Environment({Ref(herp): 'extra derp'}), Environment({Ref(herp): 'derp'}))


You can use keyword arguments, but you can also pass dictionaries directly:

    >>> String("hello").bind({"herp": "derp"}).scopes()
    (Environment({Ref(herp): 'derp'}),)

Think of this as a "mount table" for mounting objects at particular points
in a namespace.  This namespace is hierarchical:

    >>> String("hello").bind(herp = "derp", metaherp = {"a": 1, "b": {"c": 2}}).scopes()
    (Environment({Ref(herp): 'derp', Ref(metaherp.b.c): '2', Ref(metaherp.a): '1'}),)

In fact, you can bind any `Namable` object, including `List`, `Map`, and
`Struct` types directly:

    >>> class Person(Struct)
    ...   first = String
    ...   last = String
    ...
    >>> String("hello").bind(Person(first="brian")).scopes()
    (Person(first=brian),)

The `Environment` object is simply a mechanism to bind arbitrary strings
into a namespace compatible with `Namable` objects.

Because you can bind multiple times, scopes just form a name-resolution order:

    >>> (String("hello").bind(Person(first="brian"), first="john")
                        .bind({'first': "jake"}, Person(first="jane"))).scopes()
    (Person(first=jane),
     Environment({Ref(first): 'jake'}),
     Environment({Ref(first): 'john'}),
     Person(first=brian))

The later a variable is bound, the "higher priority" its name resolution
becomes.  Binding to an object is to achieve the effect of local overriding.
But you can also do a lower-priority "global" bindings via `in_scope`:

    >>> env = Environment(globalvar = "global variable", sharedvar = "global shared variable")
    >>> obj = String("hello").bind(localvar = "local variable", sharedvar = "local shared variable")
    >>> obj.scopes()
    (Environment({Ref(localvar): 'local variable', Ref(sharedvar): 'local shared variable'}),)

Now we can bind `env` directly into `obj` as if they were local variables using `bind`:

    >>> obj.bind(env).scopes()
    (Environment({Ref(globalvar): 'global variable', Ref(sharedvar): 'global shared variable'}),
     Environment({Ref(localvar): 'local variable', Ref(sharedvar): 'local shared variable'}))

Alternatively we can bind `env` into `obj` as if they were global variables using `in_scope`:

    >>> obj.in_scope(env).scopes()
    (Environment({Ref(localvar): 'local variable', Ref(sharedvar): 'local shared variable'}),
     Environment({Ref(globalvar): 'global variable', Ref(sharedvar): 'global shared variable'}))

You can see the local variables take precedence.  The use of scoping will
become more obvious when in the context of templating.


## Templating ##

### Simple templates ###

As briefly mentioned at the beginning, Mustache templates are first class
"language" features.  Let's look at the simple case of a `String` to see how
Mustache templates might behave.

    >>> String('echo {{hello_message}}')
    String(echo {{hello_message}})

OK, seems reasonable enough.  Now let's look at the more complicated version
of a `Float`:

    >>> Float('not.floaty')
    CoercionError: Cannot coerce 'not.floaty' to Float

But if we template it, it behaves differently:

    >>> Float('{{not}}.{{floaty}}')
    Float({{not}}.{{floaty}})

Pystachio understands that by introducing a Mustache template, that we
should lazily coerce the `Float` only once it's fully specified by its
environment.  For example:

    >>> not_floaty = Float('{{not}}.{{floaty}}')
    >>> not_floaty.bind({'not': 1})
    Float(1.{{floaty}})

We've bound a variable into the environment of `not_floaty`.  It's still not
floaty:

    >>> not_floaty.bind({'not': 1}).check()
    TypeCheck(FAILED): u'1.{{floaty}}' not a float

However, once it becomes fully specified, the picture changes:

    >>> floaty = not_floaty.bind({'not': 1, 'floaty': 0})
    >>> floaty
    Float(1.0)
    >>> floaty.check()
    TypeCheck(OK)

Of course, the coercion can only take place if the environment is legit:

    >>> not_floaty.bind({'not': 1, 'floaty': 'GARBAGE'})
    CoercionError: Cannot coerce '1.GARBAGE' to Float

It's worth noting that `floaty` has not been coerced permanently:

    >>> floaty
    Float(1.0)
    >>> floaty.bind({'not': 2})
    Float(2.0)

In fact, `floaty` continues to store the template; it's just hidden from
view and interpolated on-demand:

    >>> floaty._value
    '{{not}}.{{floaty}}'


As we mentioned before, objects have scopes.  Let's look at the case of floaty:

    >>> floaty = not_floaty.bind({'not': 1, 'floaty': 0})
    >>> floaty
    Float(1.0)
    >>> floaty.scopes()
    (Environment({Ref(not): '1', Ref(floaty): '0'}),)


But if we bind `not = 2`:

    >>> floaty.bind({'not': 2})
    Float(2.0)
    >>> floaty.bind({'not': 2}).scopes()
    (Environment({Ref(not): '2'}), Environment({Ref(floaty): '0', Ref(not): '1'}))

If we had merely just evaluated floaty in the scope of `not = 2`, it would have behaved differently:

    >>> floaty.in_scope({'not': 2})
    Float(1.0)

The interpolation of template variables happens in scope order from top
down.  Ultimately `bind` just prepends a scope to the list of scopes and
`in_scope` appends a scope to the end of the list of scopes.

### Complex templates ###

Remember however that you can bind any `Namable` object, which includes
`List`, `Map`, `Struct` and `Environment` types, and these are hierarchical.
Take for example a schema that defines a UNIX process:

    class Process(Struct):
      name = Default(String, '{{config.name}}')
      cmdline = String

    class ProcessConfig(Struct):
      name = String
      ports = Map(String, Integer)

The expectation could be that `Process` structures are always interpolated
in an environment where `config` is set to the `ProcessConfig`.

For example:

    >>> webserver = Process(cmdline = "bin/tfe --listen={{config.ports[http]}} --health={{config.ports[health]}}")
    >>> webserver
    Process(cmdline=bin/tfe --listen={{config.ports[http]}} --health={{config.ports[health]}}, name={{config.name}})

Now let's define its configuration:

    >>> app_config = ProcessConfig(name = "tfe", ports = {'http': 80, 'health': 8888})
    >>> app_config
    ProcessConfig(name=tfe, ports=StringIntegerMap(health => 8888, http => 80))

And let's evaluate the configuration:

    >>> webserver % Environment(config = app_config)
    Process(cmdline=bin/tfe --listen=80 --health=8888, name=tfe)

The `%`-based interpolation is just shorthand for `in_scope`.

`List` types and `Map` types are dereferenced as expected in the context of
`{{}}`-style mustache templates, using `[index]` for `List` types and
`[value]` for `Map` types.  `Struct` types are dereferenced using `.`-notation.

For example, `{{foo.bar[23][baz].bang}}` translates to a name lookup chain
of `foo (Struct) => bar (List or Map) => 23 (Map) => baz (Struct) => bang`,
ensuring the type consistency at each level of the lookup chain.

## Templating scope inheritance ##

The use of templating is most powerful in the use of `Struct` types where
parent object scope is inherited by all children during interpolation.

Let's look at the example of building a phone book type.

    class PhoneBookEntry(Struct):
      name = Required(String)
      number = Required(Integer)

    class PhoneBook(Struct):
      city = Required(String)
      people = List(PhoneBookEntry)

    >>> sf = PhoneBook(city = "San Francisco").bind(areacode = 415)
    >>> sj = PhoneBook(city = "San Jose").bind(areacode = 408)

We met a girl last night in a bar, her name was Jenny, and her number was 8
6 7 5 3 oh nayee-aye-in.  But in the bay area, you never know what her area
code could be, so we template it:

    >>> jenny = PhoneBookEntry(name = "Jenny", number = "{{areacode}}8675309")

But `brian` is a Nebraskan farm boy from the 402 and took his number with him:

    >>> brian = PhoneBookEntry(name = "Brian", number = "{{areacode}}5551234")
    >>> brian = brian.bind(areacode = 402)

If we assume that Jenny is from San Francisco, then we look her up in the San Francisco phone book:

    >>> sf(people = [jenny])
    PhoneBook(city=San Francisco, people=PhoneBookEntryList(PhoneBookEntry(name=Jenny, number=4158675309)))


But it's equally likely that she could be from San Jose:

    >>> sj(people = [jenny])
    PhoneBook(city=San Jose, people=PhoneBookEntryList(PhoneBookEntry(name=Jenny, number=4088675309)))


If we bind `jenny` to one of the phone books, she inherits the area code
from her parent object.  Of course, `brian` is from Nebraska and he kept his
number, so San Jose or San Francisco, his number remains the same:

    >>> sf(people = [jenny, brian])
    PhoneBook(city=San Francisco,
              people=PhoneBookEntryList(PhoneBookEntry(name=Jenny, number=4158675309),
                                        PhoneBookEntry(name=Brian, number=4025551234)))


## Dictionary type-checking ##

Because of how `Struct` based schemas are created, the constructor of
such a schema behaves like a deserialization mechanism from a straight
Python dictionary.  In a sense, deserialization comes for free.  Take the
schema defined below:

    class Resources(Struct):
      cpu  = Required(Float)
      ram  = Required(Integer)
      disk = Default(Integer, 2 * 2**30)

    class Process(Struct):
      name         = Required(String)
      resources    = Required(Resources)
      cmdline      = String
      max_failures = Default(Integer, 1)

    class Task(Struct):
      name         = Required(String)
      processes    = Required(List(Process))
      max_failures = Default(Integer, 1)

Let's write out a task as a dictionary, as we would expect to see from the schema:

    task = {
      'name': 'basic',
      'processes': [
        {
          'resources': {
             'cpu': 1.0,
             'ram': 100
           },
          'cmdline': 'echo hello world'
        }
      ]
    }

And instantiate it as a Task (indentation provided for clarity):

    >>> tsk = Task(task)
    >>> tsk
    Task(processes=ProcessList(Process(cmdline=echo hello world, max_failures=1,
                                       resources=Resources(disk=2147483648, ram=100, cpu=1.0))),
         max_failures=1, name=basic)


The schema that we defined as a Python class structure is applied
to the dictionary.  We can use this schema to type-check the dictionary:

    >>> tsk.check()
    TypeCheck(FAILED): Task[processes] failed: Element in ProcessList failed check: Process[name] is required.

It turns out that we forgot to specify the name of the `Process` in our
process list, and it was a `Required` field.  If we update the dictionary to
specify 'name', it will type check successfully.


## Type construction ##


It is possible to serialize constructed types, pickle them and send them
around with your dictionary data in order to do portable type checking.

### Serialization ###


Every type in Pystachio has a `serialize_type` method which is used to
describe the type in a portable way.  The basic types are uninteresting:

    >>> String.serialize_type()
    ('String',)
    >>> Integer.serialize_type()
    ('Integer',)
    >>> Float.serialize_type()
    ('Float',)

The notation is simply: `String` types are produced by the `"String"` type
factory.  They are not parameterized types so they need no additional type
parameters.  However, Lists and Maps are parameterized:

    >>> List(String).serialize_type()
    ('List', ('String',))
    >>> Map(Integer,String).serialize_type()
    ('Map', ('Integer',), ('String',))
    >>> Map(Integer,List(String)).serialize_type()
    ('Map', ('Integer',), ('List', ('String',)))

Furthermore, composite types created with `Struct` are also serializable.
Take the composite types defined in the previous section: `Task`, `Process` and `Resources`.

    >>> from pprint import pprint
    >>> pprint(Resources.serialize_type(), indent=2, width=100)
    ( 'Struct',
      'Resources',
      ('cpu', (True, (), True, ('Float',))),
      ('disk', (False, 2147483648, False, ('Integer',))),
      ('ram', (True, (), True, ('Integer',))))

In other words, the `Struct` factory is producing a type with a set of type
parameters: `Resources` is the name of the struct, `cpu`, `disk` and `ram`
are attributes of the type.

If you serialize `Task`, it recursively serializes its children types:

    >>> pprint(Task.serialize_type(), indent=2, width=100)
    ( 'Struct',
      'Task',
      ('max_failures', (False, 1, False, ('Integer',))),
      ('name', (True, (), True, ('String',))),
      ( 'processes',
        ( True,
          (),
          True,
          ( 'List',
            ( 'Struct',
              'Process',
              ('cmdline', (False, (), True, ('String',))),
              ('max_failures', (False, 1, False, ('Integer',))),
              ('name', (True, (), True, ('String',))),
              ( 'resources',
                ( True,
                  (),
                  True,
                  ( 'Struct',
                    'Resources',
                    ('cpu', (True, (), True, ('Float',))),
                    ('disk', (False, 2147483648, False, ('Integer',))),
                    ('ram', (True, (), True, ('Integer',)))))))))))


### Deserialization ###

Given a type tuple produced by serialize_type, you can then use
`TypeFactory.load` from `pystachio.typing` to load a type into an interpreter.  For example:

    >>> pprint(TypeFactory.load(Resources.serialize_type()))
    {'Float': <class 'pystachio.basic.Float'>,
     'Integer': <class 'pystachio.basic.Integer'>,
     'Resources': <class 'pystachio.typing.Resources'>}

`TypeFactory.load` returns a map from type name to the fully reified type for all types required to
describe the serialized type, including children.  In the example of `Task` above:

    >>> pprint(TypeFactory.load(Task.serialize_type()))
    {'Float': <class 'pystachio.basic.Float'>,
     'Integer': <class 'pystachio.basic.Integer'>,
     'Process': <class 'pystachio.typing.Process'>,
     'ProcessList': <class 'pystachio.typing.ProcessList'>,
     'Resources': <class 'pystachio.typing.Resources'>,
     'String': <class 'pystachio.basic.String'>,
     'Task': <class 'pystachio.typing.Task'>}

`TypeFactory.load` also takes an `into` keyword argument, so you can do
`TypeFactory.load(type, into=globals())` in order to deposit them into your interpreter:

    >>> from pystachio import *
    >>> TypeFactory.load(( 'Struct',
    ...   'Task',
    ...   ('max_failures', (False, 1, False, ('Integer',))),
    ...   ('name', (True, (), True, ('String',))),
    ...   ( 'processes',
    ...     ( True,
    ...       (),
    ...       True,
    ...       ( 'List',
    ...         ( 'Struct',
    ...           'Process',
    ...           ('cmdline', (False, (), True, ('String',))),
    ...           ('max_failures', (False, 1, False, ('Integer',))),
    ...           ('name', (True, (), True, ('String',))),
    ...           ( 'resources',
    ...             ( True,
    ...               (),
    ...               True,
    ...               ( 'Struct',
    ...                 'Resources',
    ...                 ('cpu', (True, (), True, ('Float',))),
    ...                 ('disk', (False, 2147483648, False, ('Integer',))),
    ...                 ('ram', (True, (), True, ('Integer',))))))))))), into=globals())
    >>> Task
    <class 'pystachio.typing.Task'>
    >>> Process
    <class 'pystachio.typing.Process'>
    >>> Task().check()
    TypeCheck(FAILED): Task[processes] is required.
    >>> Resources().check()
    TypeCheck(FAILED): Resources[ram] is required.
    >>> Resources(cpu = 1.0, ram = 1024, disk = 1024).check()
    TypeCheck(OK)


## Equivalence ##

Types produced by `TypeFactory.load` are reified types but they are not
identical to each other.  This could be provided in the future via type
memoization but that would require keeping some amount of state around.

Instead, `__instancecheck__` has been provided, so that you can do
`isinstance` checks:

    >>> Task
    <class 'pystachio.typing.Task'>
    >>> Task == TypeFactory.new({}, *Task.serialize_type())
    False
    >>> isinstance(Task(), TypeFactory.new({}, *Task.serialize_type()))
    True


## Author ##

@wickman (Brian Wickman)

Thanks to @marius for some of the original design ideas, @benh, @jsirois,
@wfarner and others for constructive comments.

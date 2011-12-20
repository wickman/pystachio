# Pystachio #

### tl;dr ###

Pystachio is a recursively type-checked dictionary tempating library.

### why? ###

Its primary use is for the construction of miniature DSLs.  Schemas defined
by Pystachio can themselves be serialized and reconstructed into other
Python interpreters.

The 'stache' part of Pystachio refers to the lazily interpolated Mustache
templating and scoped variable binding which is generally useful for the
construction of configuration DSLs.

## Similar projects ##

This project is unrelated to the defunct Javascript Python interpreter.

Notable related projects:

* [dictshield](http://github.com/j2labs/dictshield)
* [remoteobjects](http://github.com/saymedia/remoteobjects)
* Django's [model.Model](https://docs.djangoproject.com/en/dev/ref/models/instances/)

## Requirements ##

Tested on CPython 2.6, 2.7 and PyPy 1.6.  Most likely won't work with
CPythons pre-2.6.x.  Definitely won't work on CPython 3.2.x because of
metaclass syntax issues, but that's probably a minor change.

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

There are three basic types, two basic container types and then the `Struct` type.

### Basic Types ###

There are three basic types: the `String`, `Integer`, and `Float` types.  They behave mostly as expected:

    >>> Float(1.0).check()
    TypeCheck(OK)
    >>> String("1.0").check()
    TypeCheck(OK)
    >>> Integer(1).check()
    TypeCheck(OK)

They also make a best effort to coerce into the appropriate type:

    >>> Float("1.0")
    Float(1.0)
    >>> String(1.0)
    String(1.0)
    >>> Integer("1")
    Integer(1)

Though the same gotchas apply as standard coercion in Python:

    >>> int("1.0")
    ValueError: invalid literal for int() with base 10: '1.0'
    >>> Integer("1.0")
    pystachio.objects.CoercionError: Cannot coerce '1.0' to Integer


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
    []

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
    [{'herp': 'derp'}]

Furthermore you can bind multiple times:

    >>> String("hello").bind(herp = "derp").bind(herp = "extra derp").scopes()
    [{'herp': 'extra derp'}, {'herp': 'derp'}]


You can use keyword arguments, but you can also pass dictionaries directly:

    >>> String("hello").bind({"herp": "derp"}).scopes()
    [{'herp': 'derp'}]

In fact, you can bind any `Namable` object, including `List`, `Map`, and
`Struct` types directly:

    >>> class Person(Struct)
    ...   first = String
    ...   last = String
    ...
    >>> String("hello").bind(Person(first="brian")).scopes()
    [Person(first=brian)]

But `bind` takes keyword arguments and dictionaries as well.  These appear
to be dictionaries, but they're actually of the `pystachio.Environment`
type.  This type behaves just like a dictionary except that merges are done
differently:

    >>> # for dictionaries
    >>> d1 = {'a': {'b': 1}}
    >>> d2 = {'a': {'c': 2}}
    >>> d1.update(d2)
    >>> d1
    {'a': {'c': 2}}

In `Environment` objects, the merges are done recursively:

    >>> # for Environments
    >>> d1 = Environment({'a': {'b': 1}})
    >>> d2 = Environment({'a': {'c': 2}})
    >>> d1.merge(d2)
    >>> d1
    {'a': {'c': 2, 'b': 1}}

And in fact, when you bind variables to an object, they are bound as `Environment` variables:

    >>> type(String("hello").bind(foo = "bar").scopes()[0])
    <class 'pystachio.environment.Environment'>

There are two types of object binding: binding directly into the object via
`bind`, and binding into the object via inherited scope via `in_scope`.
Let's take the following example:

    >>> env = {'global': 'global variable', 'shared': 'global shared variable'}
    >>> obj = String("hello").bind(local = "local variable", shared = "local shared variable")
    >>> obj.scopes()
    [{'shared': 'local shared variable', 'local': 'local variable'}]

Now we can bind `env` directly into `obj` as if they were local variables using `bind`:

    >>> obj.bind(env).scopes()
    [{'shared': 'global shared variable', 'global': 'global variable'},
     {'shared': 'local shared variable', 'local': 'local variable'}]

Alternatively we can bind `env` into `obj` as if they were global variables using `in_scope`:

    >>> obj.in_scope(env).scopes()
    [{'shared': 'local shared variable', 'local': 'local variable'},
     {'shared': 'global shared variable', 'global': 'global variable'}]


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
    [{'not': 1, 'floaty': 0}]

But if we bind `not = 2`:

    >>> floaty.bind({'not': 2})
    Float(2.0)
    >>> floaty.bind({'not': 2}).scopes()
    [{'not': 2}, {'not': 1, 'floaty': 0}]


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
    ProcessConfig(name=tfe, ports=StringIntegerMap(http => 80, health => 8888))

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
                                        PhoneBookEntry(name=Brian, number=4155551234)))


## Magic ##

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
recursively to the dictionary.  In fact, we can even type check the
dictionary:

    >>> tsk.check()
    TypeCheck(FAILED): Task[processes] failed: Element in ProcessList failed check: Process[name] is required.

It turns out that we forgot to specify the name of the `Process` in our
process list, and it was a `Required` field.  If we update the dictionary to
specify 'name', it will type check successfully.


## Author ##

@wickman (Brian Wickman)

Thanks to @marius for some of the original design ideas, @benh, @jsirois,
@wfarner and others for constructive comments.

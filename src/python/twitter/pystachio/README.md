# Pystachio #

Pystachio is a library for generating structured-type overlays onto ordinary
Python objects.  Its intended use is for the construction of miniature DSLs.

The 'stache' part of Pystachio refers to the lazy referencing feature of the
generated objects, which is done exclusively with Mustache templates.  As
such, Mustache templates are first class citizens in Pystachio.


## Overview ##

You can define a structured type through the 'Composite' type:

    from twitter.pystachio import (
      Integer,
      String,
      Composite)

    class Employee(Composite):
      first = String
      last  = String
      age   = Integer


By default all fields are optional:

    >>> Employee().check()
    TypeCheck(OK)
    >>> Employee(first = 'brian')
    Employee(first=String(brian))
    >>> Employee(first = 'brian').check()
    TypeCheck(OK)


But it is possible to make certain fields required:

    from twitter.pystachio import Required

    class Employee(Composite):
      first = Required(String)
      last  = Required(String)
      age   = Integer

We can still instantiate objects with empty fields:

    >>> Employee()
    Employee()


But they will fail type checks:

    >>> Employee().check()
    TypeCheck(FAILED): Employee[last] is required.


Composite objects are purely functional and hence immutable after
constructed, however they are composable like functors:

    >>> brian = Employee(first = 'brian')
    >>> brian(last = 'wickman')
    Employee(last=String(wickman), first=String(brian))
    >>> brian
    Employee(first=String(brian))
    >>> brian = brian(last='wickman')
    >>> brian.check()
    TypeCheck(OK)


Object fields may also acquire defaults:

    class Employee(Composite):
      first    = Required(String)
      last     = Required(String)
      age      = Integer
      location = Default(String, "San Francisco")

    >>> Employee()
    Employee(location=String(San Francisco))


Schemas wouldn't be terribly useful without the ability to be hierarchical:

    class Location(Composite):
      city = String
      state = String
      country = String

    class Employee(Composite):
      first    = Required(String)
      last     = Required(String)
      age      = Integer
      location = Default(Location, Location(city = "San Francisco"))

    >>> Employee(first="brian", last="wickman")
    Employee(last=String(wickman), location=Location(city=String(San Francisco)), first=String(brian))

    >>> Employee(first="brian", last="wickman").check()
    TypeCheck(OK)


## The type system ##

There are three basic types, two basic container types and then the `Composite` type.

### Basic Types ###

There are three basic types: the `String`, `Integer`, and `Float` types.  They behave mostly as expected:

    >>> Float("1.0").check()
    TypeCheck(FAILED): '1.0' not a float
    >>> String(1.0).check()
    TypeCheck(FAILED): 1.0 not a string
    >>> Integer("1").check()
    TypeCheck(FAILED): '1' not an integer

Similarly:

    >>> Float(1.0).check()
    TypeCheck(OK)
    >>> String("1.0").check()
    TypeCheck(OK)
    >>> Integer(1).check()
    TypeCheck(OK)

### Container types ###

There are two container types: the `List` type and the `Map` type.  Lists
are parameterized by the type they contain, and Maps are parameterized from
a key type to a value type.

#### Lists ####

You construct a `List` by specifying its type (it actually behaves like a
metaclass, since it produces a type):

    >>> List(String)
    <class 'twitter.pystachio.container.StringList'>
    >>> List(String)([])
    StringList()
    >>> List(String)(["a", "b", "c"])
    StringList(String(a), String(b), String(c))

They compose like expected:

    >>> ls = List(String)
    >>> ls
    <class 'twitter.pystachio.container.StringList'>
    >>> List(ls)
    <class 'twitter.pystachio.container.StringListList'>
    >>> List(ls)([ls(["a", "b", "c"]), ls(["b", "c", "d"])])
    StringListList(StringList(String(a), String(b), String(c)), StringList(String(b), String(c), String(d)))

Type checking is not done at instantiation time:

    >>> List(ls)([ls([1, "a", "b"])])
    StringListList(StringList(String(1), String(a), String(b)))

But type checking is done recursively:

    >>> List(ls)([ls([1, "a", "b"])]).check()
    TypeCheck(FAILED): Element in StringListList failed check: Element in StringList failed check: 1 not a string

#### Maps ####

You construct a `Map` by specifying the source and destination types:

    >>> ages = Map(String, Integer)({
    ...   'brian': 30,
    ...   'ian': 15,
    ...   'robey': 5000
    ... })
    >>> ages
    StringIntegerMap(String(brian) => Integer(30), String(ian) => Integer(15), String(robey) => Integer(5000))
    >>> ages.check()
    TypeCheck(OK)

Much like all other types, these types are immutable.  The only way to
"mutate" would be to create a whole new Map.  Technically speaking you
should be able to create Maps from `Map` types or `List` types to other
types, but that is not yet supported.


## Object scopes ##


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


Objects are purely functional and hence immutable after constructed, however
they are composable like functors:

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

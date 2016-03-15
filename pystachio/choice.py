# Choice types: types that can take one of a group of selected types.

import json

from .base import Object
from .basic import SimpleObject
from .compatibility import Compatibility
from .typing import (
    Type,
    TypeCheck,
    TypeFactory,
    TypeMetaclass
)


class ChoiceFactory(TypeFactory):
    """A Pystachio type representing a value which can be one of several
    different types.
    For example, a field which could be either an integer, or an integer
    expression (where IntegerExpression is a struct type) could be written
    Choice("IntOrExpr", (Integer, IntegerExpression))
    """
    PROVIDES = 'Choice'

    @staticmethod
    def create(type_dict, *type_parameters):
        """
        type_parameters should be:
            (name, (alternative1, alternative2, ...))
        where name is a string, and the alternatives are all valid serialized
        types.
        """
        assert len(type_parameters) == 2
        name = type_parameters[0]
        alternatives = type_parameters[1]
        assert isinstance(name, Compatibility.stringy)
        assert isinstance(alternatives, (list, tuple))
        choice_types = []
        for c in alternatives:
            choice_types.append(TypeFactory.new(type_dict, *c))
        return TypeMetaclass(str(name), (ChoiceContainer,), {'CHOICES': choice_types})


class ChoiceContainer(Object, Type):
    """The inner implementation of a choice type value.

    This just stores a value, and then tries to coerce it into one of the alternatives when
    it's checked or interpolated.
    """
    __slots__ = ('_value',)

    def __init__(self, val):
        self._value = val
        self._scopes = ()

    def scopes(self):
        return self._scopes

    def get(self):
        return self._value.get()

    def value(self):
        return self._value

    def dup(self):
        return self.__class__(self._value)

    def __hash(self):
        return hash(self.get())

    def __repr__(self):
        si, _ = self.interpolate()
        return '%s(%s)' % (self.__class__.__name__,
                           repr(self._value))

    def __eq__(self, other):
        if not isinstance(other, ChoiceContainer):
            return False
        if len(self.CHOICES) != len(other.CHOICES):
            return False
        for myalt, otheralt in zip(self.CHOICES, other.CHOICES):
            if myalt.serialize_type() != other.serialize_type():
                return False
        si, _ = self.interpolate()
        oi, _ = other.interpolate()
        return si._value == other._value

    def check(self):
        # Try each of the options in sequence:
        # There are three cases for matching depending on the value:
        # (1) It's a pystachio value, and its type is the type alternative. Then typecheck
        #    succeeds.
        # (2) It's a pystachio value, but its type is not the current alternative. Then the
        #    typecheck proceeds to the next alternative.
        # (3) It's not a pystachio value. Then we try to coerce it to the type alternative.
        #    If it succeeds, then the typecheck succeeds. Otherwise, it proceeds to the next
        #    type alternative.
        # If none of the type alternatives succeed, then the check fails. match
        for opt in self.CHOICES:
            if isinstance(self._value, opt):
                return self._value.in_scope(*self.scopes()).check()
            # If this type-option is a simple-object type, then we try a
            # coercion.
            elif issubclass(opt, SimpleObject):
                try:
                    tc = opt(self._value).in_scope(*self.scopes()).check()
                    if tc.ok():
                        return tc
                except (self.CoercionError, ValueError):
                    pass
        # If we've reached here, then it failed all of its choices.
        return TypeCheck.failure(
            "%s typecheck failed: value %s did not match any of its alternatives" %
            (self.__class__.__name__, self._value))

    def interpolate(self):
        if isinstance(self._value, Object):
            return self._value.in_scope(*self.scopes()).interpolate()
        else:
            # If the value isn't a Pystachio object, then it needs to get wrapped in order to
            # interpolate it. But we don't know what type it's intended to have. So we need to try
            # to wrap it in the various type alternatives. The _first_ one that succeeds is
            # what we want to use.
            for choice_type in self.CHOICES:
                try:
                    # If this succeeds, then return it. If not, try the next type.
                    return choice_type(self._value).in_scope(*self.scopes()).interpolate()
                except (self.CoercionError, ValueError):
                    # Just proceed to the next option.
                    pass
            raise self.CoercionError(self._value, self.__class__)

    @classmethod
    def type_factory(cls):
        return 'Choice'

    @classmethod
    def type_parameters(cls):
        tup = tuple(t.serialize_type() for t in cls.CHOICES)
        return (cls.__name__, tup)

    @classmethod
    def serialize_type(cls):
        return (cls.type_factory(),) + cls.type_parameters()


def Choice(*args):
    """Helper function for creating new choice types.
    This can be called either as:
       Choice(Name, [Type1, Type2, ...])
    or:
       Choice([Type1, Type2, ...])
    In the latter case, the name of the new type will be autogenerated, and will
    look like "Choice_Type1_Type2".
    """
    if len(args) == 2:
        name, alternatives = args
    else:
        name = "Choice_" + "_".join(a.__name__ for a in args[0])
        alternatives = args[0]
    assert isinstance(name, Compatibility.stringy)
    assert all([issubclass(t, Type) for t in alternatives])
    return TypeFactory.new({}, ChoiceFactory.PROVIDES, name,
                           tuple([t.serialize_type() for t in alternatives]))

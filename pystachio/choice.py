
import copy
from inspect import isclass
import json

from .base import Object, Environment
from .basic import SimpleObject
from .compatibility import Compatibility
from .naming import Namable, frozendict
from .typing import (
  Type,
  TypeCheck,
  TypeFactory,
    TypeMetaclass)

class ChoiceFactory(TypeFactory):
    PROVIDES = 'Choice'

    @staticmethod
    def create(type_dict, *type_parameters):
        """
        type_parameters should be: (name, (alternative1, alternative2, ...))
        """
        assert len(type_parameters) == 2
        name, choices = type_parameters
        assert isinstance(name, Compatibility.stringy)
        assert isinstance(choices, (list, tuple))
        choice_types = [TypeFactory.new(type_dict, c) for c in choices]
        return TypeMetaclass(str(name), (ChoiceContainer,), { 'CHOICES': choice_types})


class ChoiceContainer(Object, Type):
#    __slots__ = ('_value', '_scopes',)
    def __init__(self, val):
        self._value = val
        self._scopes = ()
        # The value isn't a Pystachio wrapped value.

    def scopes(self):
        return self._scopes

    def get(self):
        return self._value.get()

    def dup(self):
        return self.__class__(self._value)

    def __hash(self):
        return hash(self.get())

    def __repr__(self):
#        si, _ = self.interpolate()
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
        type_checks = []
        for opt in self.CHOICES:
            if isinstance(self._value, opt):
                return self._value.in_scope(*self.scopes()).check()
            # If this type-option is a simple-object type, then we try a
            # coercion.
            elif issubclass(opt, SimpleObject):
                tc = opt(self._value).in_scope(*self.scopes()).check()
                if tc.ok():
                    return tc
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
                print("Trying choice %s" % choice_type)
                try:
                    # If this succeeds, then return it. If not, try the next type.
                    return choice_type(self._value).in_scope(*self.scopes()).interpolate()
                except self.CoercionError as e:
                    # no big deal.
                    print(e)
                    pass
            raise self.CoercionError(self._value, self.__class__)

    @classmethod
    def type_factory(cls):
        return 'Choice'

    @classmethod
    def type_parameters(cls):
        tup = tuple([t for opt_type in cls.CHOICES for t in opt_type.serialize_type()])
        return (cls.__name__, tup)

    @classmethod
    def serialize_type(cls):
        return (cls.type_factory(),) + cls.type_parameters()


def Choice(*args):
    # TODO: do some parameter type validation
    if len(args) == 2:
        name, alternatives = args
    else:
        name = "Choice_" + "_".join(a.__name__ for a in args[0])
        alternatives = args[0]

    tup = tuple([t for opt_type in alternatives for t in opt_type.serialize_type()])
    return TypeFactory.new({}, ChoiceFactory.PROVIDES, name, tup)

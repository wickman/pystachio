# Choice types: types that can take one of a group of selected types.


from .base import Object
from .compatibility import Compatibility
from .typing import Type, TypeCheck, TypeFactory, TypeMetaclass


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
    super(ChoiceContainer, self).__init__()
    self._value = val

  def get(self):
    return self.unwrap().get()

  def unwrap(self):
    """Get the Pystachio value that's wrapped in this choice."""
    return self.interpolate()[0]

  def dup(self):
    return self.__class__(self._value)

  def __hash__(self):
    return hash(self.get())

  def __unicode__(self):
    return unicode(self.unwrap())

  def __str__(self):
    return str(self.unwrap())

  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__,
                       repr(self._value))

  def __eq__(self, other):
    if not isinstance(other, ChoiceContainer):
      return False
    if len(self.CHOICES) != len(other.CHOICES):
      return False
    for myalt, otheralt in zip(self.CHOICES, other.CHOICES):
      if myalt.serialize_type() != otheralt.serialize_type():
        return False
    si, _ = self.interpolate()
    oi, _ = other.interpolate()
    return si._value == oi._value

  def _unwrap(self, ret_fun, err_fun):
    """Iterate over the options in the choice type, and try to perform some
    action on them. If the action fails (returns None or raises either CoercionError
    or ValueError), then it goes on to the next type.
    Args:
       ret_fun: a function that takes a wrapped option value, and either returns a successful
           return value or fails.
       err_fun: a function that takes the unwrapped value of this choice, and generates
           an appropriate error.
    Returns: the return value from a successful invocation of ret_fun on one of the
       type options. If no invocation fails, then returns the value of invoking err_fun.
    """
    for opt in self.CHOICES:
      if isinstance(self._value, opt):
        return ret_fun(self._value)
      else:
        try:
          o = opt(self._value)
          ret = ret_fun(o)
          if ret:
            return ret
        except (self.CoercionError, ValueError):
          pass
    return err_fun(self._value)

  def check(self):
    # Try each of the options in sequence:
    # There are three cases for matching depending on the value:
    # (1) It's a pystachio value, and its type is the type alternative. Then typecheck
    #  succeeds.
    # (2) It's a pystachio value, but its type is not the current alternative. Then the
    #  typecheck proceeds to the next alternative.
    # (3) It's not a pystachio value. Then we try to coerce it to the type alternative.
    #  If it succeeds, then the typecheck succeeds. Otherwise, it proceeds to the next
    #  type alternative.
    # If none of the type alternatives succeed, then the check fails. match
    def _check(v):
      tc = v.in_scope(*self.scopes()).check()
      if tc.ok():
        return tc

    def _err(v):
      return TypeCheck.failure(
        "%s typecheck failed: value %s did not match any of its alternatives" %
        (self.__class__.__name__, v))

    return self._unwrap(_check, _err)

  def interpolate(self):
    def _inter(v):
      return v.in_scope(*self.scopes()).interpolate()

    def _err(v):
      raise self.CoercionError(self._value, self.__class__)

    return self._unwrap(_inter, _err)

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
  assert all(issubclass(t, Type) for t in alternatives)
  return TypeFactory.new({}, ChoiceFactory.PROVIDES, name,
                         tuple(t.serialize_type() for t in alternatives))

from collections import Iterable, Mapping


class Empty(object):
  pass


class Type(object):
  PARAMETERS = ('required',)

  @classmethod
  def checker(cls):
    raise NotImplementedError

  def __init__(self, required=False, default=Empty):
    self._required = required
    self._default = default

  def required(self):
    return self._required

  def check(self, value=Empty):
    if self.required() or value is not Empty:
      return self.checker()(self._default if value is Empty else value)


class String(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, str)
    return _checker


class Integer(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, int)
    return _checker


class Float(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, float)
    return _checker


class List(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, Iterable)
    return _checker


class Map(Type):
  @classmethod
  def checker(cls):
    def _checker(value):
      return isinstance(value, Mapping)
    return _checker

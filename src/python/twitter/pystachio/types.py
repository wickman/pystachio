from collections import Iterable, Mapping


class Empty(object):
  pass


def check_required(value, required):
  return required or (not required and value is not Empty)


class Type(object):
  @classmethod
  def checker(cls):
    raise NotImplementedError

  def __init__(self, required=False):
    self._required = required

  def check(self, value):
    return self.checker()(value, required=self.required())

  def required(self):
    return self._required


class String(Type):
  @classmethod
  def checker(cls):
    def _checker(value, required):
      if check_required(value, required):
        return isinstance(value, str)
    return _checker


class Integer(Type):
  @classmethod
  def checker(cls):
    def _checker(value, required):
      if check_required(value, required):
        return isinstance(value, int)
    return _checker


class Float(Type):
  @classmethod
  def checker(cls):
    def _checker(value, required):
      if check_required(value, required):
        return isinstance(value, float)
    return _checker


class List(Type):
  @classmethod
  def checker(cls):
    def _checker(value, required):
      if check_required(value, required):
        return isinstance(value, Iterable)
    return _checker


class Map(Type):
  @classmethod
  def checker(cls):
    def _checker(value, required):
      if check_required(value, required):
        return isinstance(value, Mapping)
    return _checker

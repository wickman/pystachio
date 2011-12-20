from pystachio import Environment

def test_environment_constructors():
  oe = Environment(a = 1, b = 2)
  assert oe == {'a': 1, 'b': 2}

  oe = Environment({'a': 1, 'b': 2})
  assert oe == {'a': 1, 'b': 2}

  oe = Environment({'a': 1}, b = 2)
  assert oe == {'a': 1, 'b': 2}

  oe = Environment({'a': 1}, a = 2)
  assert oe == {'a': 2}, "last update should win"

  oe = Environment({'b': 1}, a = 2)
  assert oe == {'a': 2, 'b': 1}

  oe2 = Environment(oe, b = 2)
  assert oe2 == {'a': 2, 'b': 2}


def test_environment_merge():
  oe1 = Environment(a = 1, b = 2)
  oe2 = Environment(a = 1, b = {'c': 2})
  oe1.merge(oe2)
  assert oe1 == { 'a': 1, 'b': { 'c': 2 } }
  assert oe2 == { 'a': 1, 'b': { 'c': 2 } }

  oe1 = Environment(a = 1, b = 2)
  oe2 = Environment(a = 1, b = {'c': 2})
  oe2.merge(oe1)
  assert oe1 == { 'a': 1, 'b': 2 }
  assert oe2 == { 'a': 1, 'b': 2 }

  oe1 = Environment(a = { 'b': 1 })
  oe2 = Environment(a = { 'c': 2 })
  oe1.merge(oe2)
  assert oe1 == { 'a': {'b': 1, 'c': 2 } }
  oe2.merge(oe1)
  assert oe2 == oe1

  oe1 = Environment(a = { 'b': 1 })
  oe2 = Environment(a = None)
  oe1.merge(oe2)
  assert oe1 == { 'a': None }

  oe2 = Environment({ 'b': type })
  oe1.merge(oe2)
  assert oe1 == { 'a': None, 'b': type }

  oe2 = Environment()
  oe1.merge(oe2)
  assert oe1 == { 'a': None, 'b': type }

  oe2.merge(oe1)
  assert oe1 == oe2

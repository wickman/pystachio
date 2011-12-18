python_library(
  name = "pystachio",
  sources = rglobs("*.py") - ["repl.py"],
)

python_binary(
  name = "repl",
  source = "repl.py",
  dependencies = [pants(":pystachio")])
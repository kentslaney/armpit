# armpit
`armpit` is a python package designed to make `importlib.reload` more user
friendly. By substituting `python` for `armpit` when running a `.py` file, the
process will open an python REPL in the script's scope and use `readline` to
bind `Ctrl-H` to reloading the source.

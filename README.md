# armpit
`armpit` is a python package designed to make `importlib.reload` more user
friendly. By substituting `python` for `armpit` when running a `.py` file, the
process will open an python REPL in the script's scope and use `readline` to
bind `Ctrl-H` to reloading the source.

`armpit` also supports `-m`, the same way `python -m` does: `armpit -m pdb
script.py` opens the REPL and drops straight into `pdb` debugging
`script.py`, with everything after the module name passed through to it
untouched.

## Tests

```sh
python3 -m unittest discover -s tests
```

No dependencies required. `pytest` also works if installed
(`pip install -e .[test]`).

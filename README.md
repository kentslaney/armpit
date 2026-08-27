# armpit
`armpit` is a python package designed to make `importlib.reload` more user
friendly. By substituting `python` for `armpit` when running a `.py` file, the
process will open an python REPL in the script's scope and use `readline` to
bind `Ctrl-H` to reloading the source.

`armpit` also supports `-m`, the same way `python -m` does: `armpit -m pdb
script.py` opens the REPL and drops straight into `pdb` debugging
`script.py`, with everything after the module name passed through to it
untouched.

Python 3.14's new PyREPL ignores readline/`.inputrc` (which `armpit`'s own
`Ctrl-H` binding relies on). Pass `--basic-repl` to set `PYTHON_BASIC_REPL=1`
for the session; if your inputrc doesn't already set vi editing mode,
`armpit` runs with a temporary inputrc (layered on top of your real one via
`$include`) that does, without touching `~/.inputrc`.

## Tests

```sh
python3 -m unittest discover -s tests
```

No dependencies required. `pytest` also works if installed
(`pip install -e .[test]`).

## Releasing

The publish workflow only runs off a `v*` tag push, and reads the version
straight out of that tag, so:

```sh
git tag v1.2.3   # must match pyproject.toml's version
git push --tags
```

Run `git config core.hooksPath hooks` once per clone to enable a `pre-push`
hook that refuses to push a `vX.Y.Z` tag that doesn't match
`pyproject.toml`'s version.

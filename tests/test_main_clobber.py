import sys, types, pathlib, tempfile, shutil, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

UPDATE_SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "src" / "armpit" / "update.py"
).read_text()


class MainModuleClobberTest(unittest.TestCase):
    """Reproduces the real deployment shape: armpit.py runs as the process's
    actual `__main__` (via `python -i armpit.py ...`), and loads update.py by
    exec'ing it with armpit.py's own globals -- so `Update`'s methods share
    the exact same dict as `sys.modules["__main__"].__dict__`.

    Some `-m` targets (pdb chief among them) debug/run their target by
    clearing and rebuilding the *real* `sys.modules["__main__"]` so the
    debuggee looks like it was run directly. Since that's the same dict
    armpit's own REPL lives in, it wipes out armpit's own state -- including
    the `armpit` name itself, which is exactly what the bug report showed
    (`NameError: name 'armpit' is not defined` right after debugging with
    `armpit -m pdb ...`)."""

    def setUp(self):
        self.real_main = sys.modules.get("__main__")
        fake_main = types.ModuleType("__main__")
        sys.modules["__main__"] = fake_main
        # mirrors exactly what armpit.py does:
        #   exec(compile(open(path).read(), "update.py", "exec"), globals())
        exec(compile(UPDATE_SRC, "update.py", "exec"), fake_main.__dict__)
        self.fake_main = fake_main
        self.Update = fake_main.__dict__["armpit"]

        self.tmpdir = tempfile.mkdtemp(prefix="armpit-clobber-test-")
        sys.path.insert(0, self.tmpdir)

    def tearDown(self):
        if self.real_main is not None:
            sys.modules["__main__"] = self.real_main
        else:
            sys.modules.pop("__main__", None)
        if self.tmpdir in sys.path:
            sys.path.remove(self.tmpdir)
        while "" in sys.path:
            sys.path.remove("")
        sys.modules.pop("clobbers_main", None)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write_clobbering_module(self):
        path = pathlib.Path(self.tmpdir) / "clobbers_main.py"
        path.write_text(
            "import sys\n"
            "# this is what pdb's own _runscript does to __main__ before\n"
            "# debugging its target\n"
            "m = sys.modules['__main__']\n"
            "m.__dict__.clear()\n"
            "m.__dict__.update({'__name__': '__main__'})\n"
        )
        return path

    def test_armpit_name_survives_a_main_clobbering_target(self):
        self.write_clobbering_module()

        self.Update.from_module("clobbers_main", [])

        # the real bug: after running a `-m` target that clears
        # sys.modules["__main__"], `armpit` (the REPL's own name for the
        # Update class) must still be there
        self.assertIn("armpit", self.fake_main.__dict__)
        self.assertIs(self.fake_main.__dict__["armpit"], self.Update)

    def test_other_repl_state_also_survives(self):
        self.fake_main.__dict__["my_repl_variable"] = 12345
        self.write_clobbering_module()

        self.Update.from_module("clobbers_main", [])

        self.assertEqual(self.fake_main.__dict__.get("my_repl_variable"), 12345)

    def test_well_behaved_module_still_updates_repl_globals(self):
        # a target that *doesn't* touch __main__ should still work exactly
        # as before: its own top-level names land in the REPL globals
        path = pathlib.Path(self.tmpdir) / "well_behaved.py"
        path.write_text("WELL_BEHAVED_VALUE = 99\n")

        self.Update.from_module("well_behaved", [])

        self.assertEqual(self.fake_main.__dict__.get("WELL_BEHAVED_VALUE"), 99)
        self.assertIn("armpit", self.fake_main.__dict__)


if __name__ == "__main__":
    unittest.main()

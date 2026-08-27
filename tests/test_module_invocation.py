import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import armpit.update as update_module
from armpit import armpit as Update

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "module_invocation"


class FromModuleTest(unittest.TestCase):
    """Covers `armpit -m pkg.sub ...`: relative imports inside the target
    module need __package__ set (like real `python -m` does), and the
    module's own argv/__name__ need to be threaded through correctly."""

    def setUp(self):
        self.added_path = str(FIXTURES)
        sys.path.insert(0, self.added_path)
        self.loaded_before = list(Update.loaded)

    def tearDown(self):
        if self.added_path in sys.path:
            sys.path.remove(self.added_path)
        # `-m` always prepends "" to sys.path, like the real interpreter does
        while "" in sys.path:
            sys.path.remove("")
        for name in ("pkgtest", "pkgtest.sub"):
            sys.modules.pop(name, None)
        Update.loaded = self.loaded_before
        update_module.__dict__.pop("RESULT", None)

    def test_relative_import_and_argv_threading(self):
        Update.from_module("pkgtest.sub", ["a", "b"])

        result = update_module.RESULT
        self.assertEqual(result["name"], "__main__")
        self.assertEqual(result["package"], "pkgtest")
        self.assertEqual(result["value"], 42)
        # sys.argv[0] is the resolved file, matching what a real
        # `python -m pkgtest.sub a b` would set
        self.assertTrue(result["argv"][0].endswith("sub.py"))
        self.assertEqual(result["argv"][1:], ["a", "b"])

    def test_sys_argv_restored_after_running(self):
        before = list(sys.argv)
        Update.from_module("pkgtest.sub", ["a", "b"])
        self.assertEqual(sys.argv, before)

    def test_package_does_not_leak_into_globals(self):
        # armpit.update is itself a submodule of the `armpit` package, so it
        # always has its own __package__ == "armpit" -- what we're actually
        # guarding against is `from_module` clobbering that with the target
        # module's package name ("pkgtest") via the globals().update(scope)
        # merge that makes the executed script's names available in the REPL
        before = update_module.__dict__.get("__package__")
        Update.from_module("pkgtest.sub", [])
        self.assertEqual(update_module.__dict__.get("__package__"), before)

    def test_unknown_module_raises_import_error(self):
        with self.assertRaises(ImportError):
            Update.from_module("no_such_module_xyz", [])


if __name__ == "__main__":
    unittest.main()

import sys, os, time, shutil, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from armpit import armpit as Update

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "reload_chain"


class ReloadChainTest(unittest.TestCase):
    """Reproduces the reported bug: editing `leaf.py` (imported by `mid.py`,
    which is in turn imported by `top.py`) must reload the whole chain, not
    just `leaf` itself -- otherwise `mid`/`top` keep whatever plain value
    they pulled out of `leaf` at import time."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="armpit-reload-test-")
        for name in ("leaf.py", "mid.py", "top.py"):
            shutil.copy(FIXTURE / name, pathlib.Path(self.tmpdir) / name)
        sys.path.insert(0, self.tmpdir)

        # fresh import for each test, in case a previous run (or another
        # test file) left same-named modules behind
        for name in ("leaf", "mid", "top"):
            sys.modules.pop(name, None)
        import top
        self.top = top

        self.assertEqual(sys.modules["leaf"].VALUE, 1)
        self.assertEqual(sys.modules["mid"].MID_VALUE, 10)
        self.assertEqual(sys.modules["top"].TOP_VALUE, 11)

    def tearDown(self):
        if self.tmpdir in sys.path:
            sys.path.remove(self.tmpdir)
        for name in ("leaf", "mid", "top"):
            sys.modules.pop(name, None)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def edit_leaf(self, new_value):
        leaf_path = pathlib.Path(self.tmpdir) / "leaf.py"
        leaf_path.write_text(f"VALUE = {new_value}\n")
        # force a clearly-newer mtime so the cached-bytecode comparison
        # isn't flaky on filesystems with coarse mtime resolution
        future = time.time() + 5
        os.utime(leaf_path, (future, future))

    def test_editing_leaf_reloads_the_whole_dependent_chain(self):
        self.edit_leaf(2)

        changed = Update.reload_changed_modules()

        self.assertTrue(changed)
        self.assertEqual(sys.modules["leaf"].VALUE, 2)
        # mid recomputed MID_VALUE = LEAF_VALUE * 10 from the fresh leaf
        self.assertEqual(sys.modules["mid"].MID_VALUE, 20)
        # top recomputed TOP_VALUE = MID_VALUE + 1 from the fresh mid
        self.assertEqual(sys.modules["top"].TOP_VALUE, 21)

    def test_no_changes_means_nothing_reloads(self):
        changed = Update.reload_changed_modules()
        self.assertFalse(changed)
        self.assertEqual(sys.modules["leaf"].VALUE, 1)
        self.assertEqual(sys.modules["mid"].MID_VALUE, 10)
        self.assertEqual(sys.modules["top"].TOP_VALUE, 11)

    def test_editing_only_mid_does_not_disturb_leaf(self):
        mid_path = pathlib.Path(self.tmpdir) / "mid.py"
        mid_path.write_text(
            "from leaf import VALUE as LEAF_VALUE\n"
            "MID_VALUE = LEAF_VALUE * 100\n")
        future = time.time() + 5
        os.utime(mid_path, (future, future))

        changed = Update.reload_changed_modules()

        self.assertTrue(changed)
        self.assertEqual(sys.modules["leaf"].VALUE, 1)
        self.assertEqual(sys.modules["mid"].MID_VALUE, 100)
        self.assertEqual(sys.modules["top"].TOP_VALUE, 101)


class ModuleDependencyGraphTest(unittest.TestCase):
    """module_imports/module_dependencies are source-level (AST-based), so
    they catch plain-value imports too, not just functions/classes/modules
    (which is the one thing a runtime `__module__`-based heuristic would
    have missed)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="armpit-depgraph-test-")
        for name in ("leaf.py", "mid.py", "top.py"):
            shutil.copy(FIXTURE / name, pathlib.Path(self.tmpdir) / name)
        sys.path.insert(0, self.tmpdir)
        for name in ("leaf", "mid", "top"):
            sys.modules.pop(name, None)
        import top
        self.top = top

    def tearDown(self):
        if self.tmpdir in sys.path:
            sys.path.remove(self.tmpdir)
        for name in ("leaf", "mid", "top"):
            sys.modules.pop(name, None)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_mid_depends_on_leaf(self):
        known = set(sys.modules.keys())
        deps = Update.module_dependencies(sys.modules["mid"], known)
        self.assertEqual(deps, {"leaf"})

    def test_top_depends_on_mid_only_directly(self):
        known = set(sys.modules.keys())
        deps = Update.module_dependencies(sys.modules["top"], known)
        self.assertEqual(deps, {"mid"})

    def test_leaf_has_no_dependencies(self):
        known = set(sys.modules.keys())
        deps = Update.module_dependencies(sys.modules["leaf"], known)
        self.assertEqual(deps, set())


if __name__ == "__main__":
    unittest.main()

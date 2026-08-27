import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from armpit.cli import split_module_invocation


class SplitModuleInvocationTest(unittest.TestCase):
    def test_no_dash_m_is_passed_through_unchanged(self):
        argv, module, module_args = split_module_invocation(["script.py"])
        self.assertEqual(argv, ["script.py"])
        self.assertIsNone(module)
        self.assertEqual(module_args, [])

    def test_dash_m_pdb_with_script_and_flags(self):
        argv, module, module_args = split_module_invocation(
            ["-m", "pdb", "script.py", "--foo", "bar"])
        self.assertEqual(argv, [])
        self.assertEqual(module, "pdb")
        # everything after the module name is untouched, including flags
        # that would otherwise look like armpit's own options
        self.assertEqual(module_args, ["script.py", "--foo", "bar"])

    def test_armpit_options_before_dash_m_are_kept(self):
        argv, module, module_args = split_module_invocation(
            ["--bind-none", "-m", "json.tool", "x.json"])
        self.assertEqual(argv, ["--bind-none"])
        self.assertEqual(module, "json.tool")
        self.assertEqual(module_args, ["x.json"])

    def test_bare_dash_m_with_no_module_name_errors(self):
        with self.assertRaises(SystemExit):
            split_module_invocation(["-m"])

    def test_dash_m_with_no_trailing_args(self):
        argv, module, module_args = split_module_invocation(["-m", "pdb"])
        self.assertEqual(argv, [])
        self.assertEqual(module, "pdb")
        self.assertEqual(module_args, [])


if __name__ == "__main__":
    unittest.main()

import os, sys, pathlib, tempfile, unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import armpit.cli as cli
from armpit.cli import (
    resolve_inputrc_path, inputrc_has_vi_mode, write_temp_vi_inputrc)


class ResolveInputrcPathTest(unittest.TestCase):
    def setUp(self):
        self.saved_inputrc = os.environ.get("INPUTRC")

    def tearDown(self):
        if self.saved_inputrc is None:
            os.environ.pop("INPUTRC", None)
        else:
            os.environ["INPUTRC"] = self.saved_inputrc

    def test_prefers_inputrc_env_var(self):
        os.environ["INPUTRC"] = "/some/custom/path"
        self.assertEqual(resolve_inputrc_path(), "/some/custom/path")

    def test_falls_back_to_home_inputrc(self):
        os.environ.pop("INPUTRC", None)
        self.assertEqual(
            resolve_inputrc_path(), os.path.expanduser("~/.inputrc"))


class InputrcHasViModeTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="armpit-inputrc-test-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write(self, content):
        path = pathlib.Path(self.tmpdir) / "inputrc"
        path.write_text(content)
        return str(path)

    def test_missing_file_has_no_vi_mode(self):
        missing = str(pathlib.Path(self.tmpdir) / "does-not-exist")
        self.assertFalse(inputrc_has_vi_mode(missing))

    def test_empty_inputrc_has_no_vi_mode(self):
        path = self.write("")
        self.assertFalse(inputrc_has_vi_mode(path))

    def test_emacs_mode_is_not_vi_mode(self):
        path = self.write("set editing-mode emacs\n\"\\C-h\": backward-char\n")
        self.assertFalse(inputrc_has_vi_mode(path))

    def test_detects_vi_mode(self):
        path = self.write("set editing-mode vi\nset show-mode-in-prompt on\n")
        self.assertTrue(inputrc_has_vi_mode(path))

    def test_detects_vi_mode_with_extra_whitespace(self):
        path = self.write("set   editing-mode\tvi   \n")
        self.assertTrue(inputrc_has_vi_mode(path))

    def test_none_path_has_no_vi_mode(self):
        self.assertFalse(inputrc_has_vi_mode(None))


class WriteTempViInputrcTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="armpit-inputrc-test-")
        self.created = []

    def tearDown(self):
        import shutil
        for path in self.created:
            try:
                os.remove(path)
            except OSError:
                pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_existing_inputrc_just_sets_vi_mode(self):
        missing = str(pathlib.Path(self.tmpdir) / "does-not-exist")
        temp_path = write_temp_vi_inputrc(missing)
        self.created.append(temp_path)

        content = pathlib.Path(temp_path).read_text()
        self.assertNotIn("$include", content)
        self.assertTrue(inputrc_has_vi_mode(temp_path))

    def test_existing_inputrc_is_included_not_copied(self):
        existing = pathlib.Path(self.tmpdir) / "inputrc"
        existing.write_text('"\\C-x\\C-r": re-read-init-file\n')

        temp_path = write_temp_vi_inputrc(str(existing))
        self.created.append(temp_path)

        content = pathlib.Path(temp_path).read_text()
        self.assertIn(f"$include {existing}", content)
        # the real file's content is referenced, not duplicated into the
        # temp file -- editing the original still takes effect
        self.assertNotIn("re-read-init-file", content)
        self.assertTrue(inputrc_has_vi_mode(temp_path))

    def test_does_not_touch_the_original_file(self):
        existing = pathlib.Path(self.tmpdir) / "inputrc"
        original_content = 'set editing-mode emacs\n'
        existing.write_text(original_content)

        temp_path = write_temp_vi_inputrc(str(existing))
        self.created.append(temp_path)

        self.assertEqual(existing.read_text(), original_content)
        self.assertNotEqual(temp_path, str(existing))


class MainBasicReplIntegrationTest(unittest.TestCase):
    """--basic-repl is wired up correctly in main(): env vars set before
    pty.spawn, temp inputrc written/pointed-to when needed, and cleaned up
    afterward -- without actually spawning a REPL."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="armpit-main-test-")
        self.saved_env = dict(os.environ)
        os.environ.pop("PYTHON_BASIC_REPL", None)
        os.environ.pop("INPUTRC", None)

    def tearDown(self):
        import shutil
        os.environ.clear()
        os.environ.update(self.saved_env)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def run_main(self, argv):
        with mock.patch.object(sys, "argv", ["armpit", *argv]), \
                mock.patch.object(cli.pty, "spawn") as spawn:
            cli.main()
        return spawn

    def test_basic_repl_sets_env_var(self):
        script = pathlib.Path(self.tmpdir) / "script.py"
        script.write_text("pass\n")
        self.run_main(["--basic-repl", str(script)])
        self.assertEqual(os.environ.get("PYTHON_BASIC_REPL"), "1")

    def test_basic_repl_without_existing_vi_mode_uses_temp_inputrc(self):
        inputrc = pathlib.Path(self.tmpdir) / "inputrc"
        inputrc.write_text("set editing-mode emacs\n")
        os.environ["INPUTRC"] = str(inputrc)
        script = pathlib.Path(self.tmpdir) / "script.py"
        script.write_text("pass\n")

        self.run_main(["--basic-repl", str(script)])

        temp_path = os.environ.get("INPUTRC")
        self.assertNotEqual(temp_path, str(inputrc))
        # cleaned up after the (mocked) session ends
        self.assertFalse(os.path.exists(temp_path))

    def test_basic_repl_with_existing_vi_mode_leaves_inputrc_alone(self):
        inputrc = pathlib.Path(self.tmpdir) / "inputrc"
        inputrc.write_text("set editing-mode vi\n")
        os.environ["INPUTRC"] = str(inputrc)
        script = pathlib.Path(self.tmpdir) / "script.py"
        script.write_text("pass\n")

        self.run_main(["--basic-repl", str(script)])

        self.assertEqual(os.environ.get("INPUTRC"), str(inputrc))

    def test_without_the_flag_nothing_is_touched(self):
        script = pathlib.Path(self.tmpdir) / "script.py"
        script.write_text("pass\n")

        self.run_main([str(script)])

        self.assertIsNone(os.environ.get("PYTHON_BASIC_REPL"))
        self.assertIsNone(os.environ.get("INPUTRC"))


if __name__ == "__main__":
    unittest.main()

import pty, sys, os.path, argparse, re, tempfile

class ArgString(str):
    def __new__(cls, manual, *a, **kw):
        return super().__new__(cls, *a, **kw)

    def __init__(self, manual, *a, **kw):
        super().__init__()
        self.manual = manual

class ManualAction(argparse.Action):
    def __init__(
            self, option_strings, dest, nargs=None, const=None, default=None,
            *a, **kw):
        default = ArgString(False, default)
        super().__init__(option_strings, dest, nargs, const, default, *a, **kw)

    def __call__(self, parser, namespace, values, option_string=None):
        assert isinstance(values, str) and len(values) == 1
        setattr(namespace, self.dest, ArgString(True, values))

parser = argparse.ArgumentParser(description="Python incremental revision")
# incremental revision -> import iterator -> impit -> armpit
parser.add_argument("paths", nargs="*", help="Python script paths")
group = parser.add_mutually_exclusive_group()
group.add_argument(
    "--bind-none", dest="bind", action="store_const", const=0, help=(
        "run the CLI without keybindings, controlling reloads through the "
        "`armpit` global variable"))
group.add_argument(
    "--bind-rerun", dest="bind", action="store_const", const=3, help=(
        "add keybindings for both soft and hard reloads: the former will "
        "fail if it can't detect changes since the last run"))
group.add_argument(
    "--bind-rerun-only", dest="bind", action="store_const", const=2, help=(
        "adds a keybinding for hard reloading based on the `primary` option; "
        "this option is useful if changes aren't being detected"))
group.set_defaults(bind=1)

parser.add_argument("--primary", default="h", action=ManualAction, help=(
    "specify the hotkey to softest bound reload "
    "(default: h, will warn if the default is bound)"))
parser.add_argument("--secondary", default="o", action=ManualAction, help=(
    "specify the hotkey to bind to hard reload if both reload types are bound "
    "(default: o, will warn if the default is bound)"))

parser.add_argument("--main", action="store_true", help=(
    'run with `__name__ == "__main__"`'))
parser.add_argument("--flat-path", action="store_true", help=(
    "add the parent directory for the file being executed to sys.path"))

group = parser.add_mutually_exclusive_group()
group.add_argument("--package", default=False, nargs="?", help=(
    "specify a path for the parent package; specifying the flag without an "
    "argument is an alias for `--flat-package`; this option adds the package's "
    "parent directory to sys.path, meaning import resolution may deviate "
    "slightly from the default behavior"))
group.add_argument(
        "--cwd-package", dest="package", action="store_const", const=".", help=(
            "specify the current working directory as the parent package path; "
            "this is the same as specifying `--package .`"))
group.add_argument(
        "--flat-package", dest="package", action="store_const", const=None,
        help=(
            "specify the parent package as the directory containing the script "
            "being run"))

parser.add_argument("--basic-repl", action="store_true", help=(
    "set PYTHON_BASIC_REPL=1 so Python 3.14+'s new PyREPL doesn't ignore "
    "readline/.inputrc (which armpit's own keybinding relies on); if the "
    "active inputrc doesn't already set vi editing mode, run with a "
    "temporary inputrc -- layered on top of the real one, via $include -- "
    "that does, without touching ~/.inputrc"))

def split_module_invocation(argv):
    """Mimic `python -m module ...`: everything after a bare `-m` is passed
    through untouched as the module's own argv, rather than being parsed as
    armpit's own options.

    Returns (remaining_argv, module_name_or_None, module_args).
    """
    argv = list(argv)
    if "-m" not in argv:
        return argv, None, []
    idx = argv.index("-m")
    if idx + 1 >= len(argv):
        parser.error("argument -m: expected one argument")
    module, module_args = argv[idx + 1], argv[idx + 2:]
    return argv[:idx], module, module_args

VI_MODE_RE = re.compile(r'(?im)^[ \t]*set[ \t]+editing-mode[ \t]+vi[ \t]*$')

def resolve_inputrc_path():
    """Where GNU readline would look for the user's own inputrc: $INPUTRC
    if set, otherwise ~/.inputrc. (readline also always reads /etc/inputrc
    first as a system-wide base -- that's untouched by any of this.)"""
    return os.environ.get("INPUTRC") or os.path.expanduser("~/.inputrc")

def inputrc_has_vi_mode(path):
    """Whether `path` itself declares `set editing-mode vi`. Doesn't follow
    $include chains inside the file -- good enough for "did the user already
    opt into vi bindings", which is what this is actually deciding."""
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
        return False
    return bool(VI_MODE_RE.search(content))

def write_temp_vi_inputrc(existing_path):
    """A standalone inputrc, in a new temp file, that $includes whatever the
    user already has (if anything) and then forces vi editing mode. Returns
    the temp file's path; the caller is responsible for removing it."""
    fd, path = tempfile.mkstemp(prefix="armpit-inputrc-", suffix=".inputrc")
    with os.fdopen(fd, "w") as f:
        if existing_path and os.path.isfile(existing_path):
            f.write(f"$include {existing_path}\n")
        f.write("set editing-mode vi\n")
    return path

def main():
    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, "armpit.py")

    argv, module, module_args = split_module_invocation(sys.argv[1:])
    args = parser.parse_args(argv)
    if module is not None and args.paths:
        parser.error("argument -m: not allowed with script paths")

    bind = args.bind + 4 * (not args.primary.manual)
    bind += 8 * (not args.secondary.manual)

    package = args.package is not None and args.package is not False
    package_path = [args.package] if package else []
    package = package + 2 * (args.package is not False)
    package = package + 4 * args.flat_path + 8 * args.main

    ctrl = hex(bind)[2:] + args.primary + args.secondary + str(package)
    target = ["-m", module, *module_args] if module is not None else args.paths

    temp_inputrc = None
    if args.basic_repl:
        os.environ["PYTHON_BASIC_REPL"] = "1"
        if not inputrc_has_vi_mode(resolve_inputrc_path()):
            temp_inputrc = write_temp_vi_inputrc(resolve_inputrc_path())
            os.environ["INPUTRC"] = temp_inputrc

    try:
        pty.spawn(["python", "-i", path, ctrl] + package_path + target)
    finally:
        if temp_inputrc is not None:
            try:
                os.remove(temp_inputrc)
            except OSError:
                pass

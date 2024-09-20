import pty, sys, os.path, argparse

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

def main():
    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, "armpit.py")

    args = parser.parse_args()
    bind = args.bind + 4 * (not args.primary.manual)
    bind += 8 * (not args.secondary.manual)

    package = args.package is not None and args.package is not False
    package_path = [args.package] if package else []
    package = package + 2 * (args.package is not False)
    package = package + 4 * args.flat_path + 8 * args.main

    ctrl = hex(bind)[2:] + args.primary + args.secondary + str(package)
    pty.spawn(["python", "-i", path, ctrl] + package_path + args.paths)

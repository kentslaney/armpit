def armpit():
    import os, readline, datetime, traceback, logging, sys, importlib, \
            pathlib, types, ast

    def ago(date):
        diff = datetime.datetime.now() - date
        units = (
            (diff.days, "d"),
            (diff.seconds // 3600, "h"),
            ((diff.seconds % 3600) // 60, "m"),
            (diff.seconds % 60, "s"),
            (diff.microseconds // 1000, "ms"),
            (diff.microseconds % 1000, "\u03BCs")
        )

        for n, (i, _) in enumerate(units):
            if i > 0:
                break
        units = units[n:]

        units = units[:1] if len(units) <= 2 else units[:-2]
        units = " ".join(str(i) + j for i, j in units)
        return "\33\x5b1m\33\x5b34m" + units + "\33\x5b0m"

    def classmaps(f):
        @classmethod
        def wrapper(cls, *a, **kw):
            for i in cls.loaded:
                f(i, *a, **kw)
            cls.package_hooks = cls.package_hooks or []
            cls.package_hooks.append(lambda self: f(self, *a, **kw))
        return wrapper

    class FileUnmodifiedError(ImportError):
        pass

    class Update:
        loaded, package_hooks = (), ()
        rerun_binding = None
        name = None

        def __init__(self, path, argv=None, name=None, package_name=None):
            self.path = pathlib.Path(path).resolve()
            self.fname = self.path.name
            self.name, ext = name or self.name or self.path.stem, self.path.suffix
            self.prev = None
            self.package_path = None
            self.argv = argv
            self.package_name = package_name
            if not os.path.isfile(self.path):
                raise FileNotFoundError(f"No such file or directory: '{path}'")
            elif not ext == '.py':
                raise ImportError(
                    f"Unable to open non-python file '{self.fname}'")
            if not any(mod.path == self.path for mod in self.loaded):
                self.__class__.loaded = self.loaded or []
                self.__class__.loaded.append(self)

            for i in self.package_hooks:
                i(self)

            try:
                self.update()
            except:
                traceback.print_exc()

        @property
        def lastedit(self):
            return datetime.datetime.fromtimestamp(self.path.stat().st_mtime)

        @property
        def updated(self):
            return not self.prev or self.lastedit > self.prev

        def __call__(self):
            if not self.updated:
                raise FileUnmodifiedError(
                    f"No changes made: '{self.fname}' last modified "
                    f"{ago(self.lastedit)} ago, module reloaded "
                    f"{ago(self.prev)} ago")

            return self.update()

        _removals = None
        def python_path(self, adding):
            self._removals = [] if self._removals is None else self._removals
            existing = tuple(map(pathlib.Path, sys.path))
            if not any(i.is_dir() and i.samefile(adding) for i in existing):
                sys.path.insert(0, str(adding))
                self._removals.append(adding)

        def reset_path(self):
            for i in self._removals or ():
                if str(i) in sys.path:
                    sys.path.remove(str(i))

        @classmaps
        def flat_path(self):
            self.python_path(self.path.parent)

        @classmaps
        def cwd_package(self):
            self.package_path = pathlib.Path.cwd()

        @classmaps
        def flat_package(self):
            self.package_path = self.path.parent

        @classmaps
        def set_package(self, path):
            self.package_path = pathlib.Path(path).resolve()

        @classmethod
        def reset_package(cls):
            cls.package_hooks = ()

        def package(self, scope):
            if self.package_path is None:
                return
            assert self.package_path.is_dir()
            assert any(map(self.package_path.samefile, self.path.parents))
            self.python_path(self.package_path)
            self.python_path(self.package_path.parent)
            scope["__package__"] = self.package_path.name

        def update(self):
            event = 'loaded' if self.updated else 'rerun'
            scope = {"__name__": self.name, "__file__": self.path}
            if self.argv is not None:
                # only set for `-m` invocations, matching what
                # runpy._run_module_as_main does, so relative imports inside
                # a submodule (e.g. `-m pkg.sub`) resolve correctly
                scope["__package__"] = self.package_name
            with open(self.path) as f:
                source = compile(f.read(), self.fname, "exec")
            self.prev = datetime.datetime.now()

            self.package(scope)
            if self.argv is not None:
                prev_argv, sys.argv = sys.argv, self.argv

            # some `-m` targets (pdb chief among them) run/debug their
            # target by repurposing the *real* sys.modules["__main__"] --
            # e.g. pdb clears and rebuilds it wholesale so the debuggee
            # looks like it was run directly. Since armpit's own REPL lives
            # in that same __main__ (`python -i` keeps the script's globals
            # as the REPL's), that wipes out armpit's own state, including
            # the `armpit` name itself. Snapshot it beforehand so anything
            # that goes missing is restored afterwards.
            main = sys.modules.get("__main__")
            before = dict(main.__dict__) if self.argv is not None and main else None

            try:
                exec(source, scope)
            finally:
                if self.argv is not None:
                    sys.argv = prev_argv
                print(f"Module '{self.fname}' {event} in {ago(self.prev)}")
                del scope["__name__"], scope["__file__"]
                scope.pop("__package__", None)
                globals().update(scope)
                if before is not None:
                    main = sys.modules.get("__main__")
                    if main is not None:
                        for key, value in before.items():
                            main.__dict__.setdefault(key, value)

        @classmethod
        def from_module(cls, name, argv=()):
            # mimic `python -m name ...`: locate the module the same way the
            # interpreter does (including packages that dispatch to a
            # `__main__` submodule), forcing __name__ == "__main__" and
            # prepending the cwd to sys.path like the real `-m` flag does
            import runpy
            if sys.path[:1] != [""]:
                sys.path.insert(0, "")
            try:
                _, spec, _ = runpy._get_module_details(name)
            except ImportError as e:
                raise ImportError(f"No module named {name!r}") from e
            return cls(
                spec.origin, argv=[spec.origin, *argv], name="__main__",
                package_name=spec.parent)

        @classmethod
        def ref(cls):
            return f"{cls.__qualname__}"

        @classmethod
        def current(cls, force=False):
            if not cls.loaded:
                raise ImportError(
                    f"No modules to update, add one with `{cls.ref()}(<path>)`")

            force |= cls.reload_modules() if force else \
                    cls.reload_changed_modules()
            err = []
            for module in cls.loaded:
                try:
                    if force:
                        module.update()
                    else:
                        module()
                except FileUnmodifiedError as e:
                    err.append(e)
            if len(err) == len(cls.loaded):
                for e in err:
                    print(e)
                if cls.rerun_binding is None:
                    print(
                        f"Run `{cls.ref()}.rerun()` to force an update")
                else:
                    print(
                        f"Run `{cls.ref()}.rerun()` or use "
                        f"'{cls.rerun_binding}' to force an update")

        @classmethod
        def rerun(cls):
            cls.reload_modules()
            return cls.current(True)

        @staticmethod
        def reload_modules():
            for module in sys.modules.values():
                importlib.reload(module)

        @staticmethod
        def module_changed(module):
            """Whether `module`'s source is newer than its compiled cache,
            i.e. whether it was edited since it was last imported/reloaded."""
            if not hasattr(module, "__cached__"):
                return False
            if isinstance(module.__cached__, types.ModuleType):
                return False
            cached = pathlib.Path(module.__cached__)
            if not cached.is_file():
                return False
            mtime = cached.stat().st_mtime
            paths = getattr(module, "__path__", []) + [module.__file__]
            files = [i for i in map(pathlib.Path, paths) if i.is_file()]
            if not files:
                return False
            latest = min(i.stat().st_mtime for i in files)
            return latest > mtime

        @staticmethod
        def module_imports(module):
            """The module names `module`'s source directly imports, both
            `import x` and `from x import y` -- including `y` itself, in
            case it's a submodule rather than an attribute (`from pkg import
            sub`). Relative imports (`from . import x`) are resolved against
            the module's own `__package__`. This is a static, source-level
            read: it doesn't depend on what kind of object ended up bound
            (plain values have no runtime trace back to where they came
            from, unlike functions/classes/modules)."""
            path = getattr(module, "__file__", None)
            if not path or not str(path).endswith(".py"):
                return set()
            try:
                tree = ast.parse(pathlib.Path(path).read_text())
            except (OSError, SyntaxError, ValueError):
                return set()

            package = getattr(module, "__package__", None) or ""
            names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        names.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if not node.level:
                        base = node.module
                    else:
                        parts = package.split(".") if package else []
                        up = node.level - 1
                        base_parts = parts[:len(parts) - up] if up else parts
                        base = ".".join(
                                p for p in [*base_parts, node.module] if p)
                    if not base:
                        continue
                    names.add(base)
                    for alias in node.names:
                        names.add(f"{base}.{alias.name}")
            return names

        @staticmethod
        def resolve_known(names, known):
            """Collapse dotted names down to whichever prefix is an actually
            loaded module, e.g. "pkg.sub.attr" -> "pkg.sub" if that's what's
            loaded and "attr" is just something pulled out of it."""
            resolved = set()
            for name in names:
                while name:
                    if name in known:
                        resolved.add(name)
                        break
                    name = name.rpartition(".")[0]
            return resolved

        @classmethod
        def module_dependencies(cls, module, known):
            deps = cls.resolve_known(cls.module_imports(module), known)
            return deps - {module.__name__}

        @classmethod
        def reload_changed_modules(cls):
            names = tuple(sys.modules.keys())
            known = set(names)

            changed = {
                name for name in names
                if cls.module_changed(sys.modules[name])}
            if not changed:
                return False

            deps = {
                name: cls.module_dependencies(sys.modules[name], known)
                for name in names}
            dependents = {name: set() for name in names}
            for name, imports in deps.items():
                for dep in imports:
                    dependents[dep].add(name)

            # anything that (directly or transitively) imports a changed
            # module needs reloading too, or it keeps a stale reference to
            # whatever it pulled out of that module -- `from dep import
            # thing` binds `thing` once, at import time, and isn't updated
            # just because `dep` itself gets reloaded
            stale, frontier = set(changed), set(changed)
            while frontier:
                frontier = {
                    dependent
                    for name in frontier
                    for dependent in dependents.get(name, ())
                    if dependent not in stale}
                stale |= frontier

            # reload dependencies before dependents, so a re-executed
            # `from dep import thing` observes dep's already-refreshed state
            ordered, seen = [], set()
            def visit(name):
                if name in seen or name not in stale:
                    return
                seen.add(name)
                for dep in deps.get(name, ()):
                    visit(dep)
                ordered.append(name)
            for name in names:
                visit(name)

            for name in ordered:
                module = sys.modules.get(name)
                if module is None:
                    continue
                print("reloading module", name)
                try:
                    importlib.reload(module)
                except ModuleNotFoundError:
                    pass
            return True

        @classmethod
        def bind(cls, keys=r'\C-o', f="rerun", warn=True):
            # C-[HOQ] are unmapped by default
            # https://vhernando.github.io/keyboard-shorcuts-bash-readline-default
            if f == "rerun":
                cls.rerun_binding = keys
            if warn:
                logging.warning(
                    f"key binding '{keys}' has been remapped "
                    f"as a macro for {cls.ref()}.{f}()")
            readline.parse_and_bind(f'{keys}: "\\e[H{cls.ref()}.{f}()#\n"')

    return Update

armpit = armpit()

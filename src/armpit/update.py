def armpit():
    import os, readline, datetime, traceback, logging, sys, importlib, pathlib,\
            types

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

        def __init__(self, path):
            self.path = pathlib.Path(path).resolve()
            self.fname = self.path.name
            self.name, ext = self.name or self.path.stem, self.path.suffix
            self.prev = None
            self.package_path = None
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
            source = compile(open(self.path).read(), self.fname, "exec")
            self.prev = datetime.datetime.now()

            self.package(scope)
            try:
                exec(source, scope)
            finally:
                print(f"Module '{self.fname}' {event} in {ago(self.prev)}")
                del scope["__name__"], scope["__file__"]
                globals().update(scope)

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
        def reload_changed_modules():
            checking, changed = tuple(sys.modules.keys()), False
            for package in checking:
                module = sys.modules[package]
                if not hasattr(module, "__cached__"):
                    continue
                if isinstance(module.__cached__, types.ModuleType):
                    continue
                cached = pathlib.Path(module.__cached__)
                if not cached.is_file():
                    continue
                mtime = cached.stat().st_mtime
                paths = getattr(module, "__path__", []) + [module.__file__]
                latest = min(
                        i.stat().st_mtime for i in map(pathlib.Path, paths)
                        if i.is_file())
                if latest > mtime:
                    changed = True
                    print("reloading module", package)
                    try:
                        importlib.reload(module)
                    except ModuleNotFoundError:
                        pass
            return changed

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

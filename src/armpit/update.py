def armpit():
    import os, readline, datetime, traceback, logging

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
        return "\33[1m\33[34m" + units + "\33[0m"

    class FileUnmodifiedError(ImportError):
        pass

    class Update:
        loaded, rerun_binding = [], None

        def __init__(self, path):
            self.path = os.path.abspath(os.path.expanduser(path))
            self.fname = os.path.basename(self.path)
            self.name, ext = os.path.splitext(self.fname)
            self.prev = None
            if not os.path.isfile(self.path):
                raise FileNotFoundError(f"No such file or directory: '{path}'")
            elif not self.path.endswith('.py'):
                raise ImportError(
                    f"Unable to open non-python file '{self.fname}'")
            if not any(module.path == self.path for module in self.loaded):
                self.__class__.loaded.append(self)

            try:
                self.update()
            except:
                traceback.print_exc()

        @property
        def lastedit(self):
            return datetime.datetime.fromtimestamp(os.stat(self.path).st_mtime)

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

        def update(self):
            event = 'loaded' if self.updated else 'rerun'
            scope = {"__name__": self.name, "__file__": self.path}
            source = compile(open(self.path).read(), self.fname, "exec")
            self.prev = datetime.datetime.now()

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
            return cls.current(True)

        @classmethod
        def bind(cls, keys=r'\C-o', f="rerun"):
            # C-[HOQ] are unmapped by default
            # https://vhernando.github.io/keyboard-shorcuts-bash-readline-default
            if f == "rerun":
                cls.rerun_binding = keys
            logging.warning(
                f"key binding '{keys}' has been remapped "
                f"as a macro for {cls.ref()}.{f}()")
            readline.parse_and_bind(f'{keys}: "\\e[H{cls.ref()}.{f}()#\n"')

    class Armpit(Update):
        # "incremental revision" --> "import iterator" --> "impit" --> "armpit"
        # factory implementation without transitioning away from modifying cls
        def __new__(cls):
            return type(cls.__name__, (Update,), {
                **Update.__dict__, "loaded": []})

    return Armpit

armpit = armpit()
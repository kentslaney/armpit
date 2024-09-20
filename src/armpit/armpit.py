def armpit():
    global armpit
    import os, sys

    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, "update.py")

    bind, primary, secondary, packaged = sys.argv[1]
    bind, packaged = int(bind, 16), int(packaged, 16)

    exec(compile(open(path).read(), "update.py", "exec"), globals())
    class armpit(armpit):
        name = "__main__" if packaged & 8 else None

    if packaged & 4:
        armpit.flat_path()
    if packaged & 2:
        if packaged & 1:
            armpit.set_package(sys.argv[2])
        else:
            armpit.flat_package()

    for module in sys.argv[2 + (packaged & 1):]:
        armpit(module)

    if bind & 1:
        armpit.bind(r'\C-' + primary, 'current', bind & 4)
    if bind & 2:
        key = secondary if bind & 1 else primary
        armpit.bind(r'\C-' + key, 'rerun', bind & 8)

armpit()

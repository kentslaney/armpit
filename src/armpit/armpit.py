def armpit():
    global armpit
    import os, sys

    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, "update.py")

    exec(compile(open(path).read(), "update.py", "exec"), globals())
    class armpit(armpit()):
        pass

    bind = int(sys.argv[1])
    for module in sys.argv[2:]:
        armpit(module)
    
    if bind & 1:
        armpit.bind('\C-h', 'current')
    if bind & 2:
        armpit.bind('\C-o', 'rerun')

armpit()

import pty, sys, os.path, argparse

parser = argparse.ArgumentParser(description="Python incremental revision")
parser.add_argument("paths", nargs="*", help="python script paths")
group = parser.add_mutually_exclusive_group()
group.add_argument("--bind-none", dest="bind", action="store_const", const=0)
group.add_argument("--bind-rerun", dest="bind", action="store_const", const=3)
group.add_argument(
    "--bind-rerun-only", dest="bind", action="store_const", const=2)
group.set_defaults(bind=1)


def main():
    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, "armpit.py")

    args = parser.parse_args()
    pty.spawn(["python", "-i", path, str(args.bind)] + args.paths)

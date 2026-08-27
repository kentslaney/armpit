import sys

# a relative import, like `python -m pkgtest.sub` needs __package__ set
# correctly for
from . import VALUE

RESULT = {
    "name": __name__,
    "package": __package__,
    "argv": list(sys.argv),
    "value": VALUE,
}

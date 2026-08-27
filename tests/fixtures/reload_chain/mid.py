from leaf import VALUE as LEAF_VALUE

# a plain value computed once at import time -- this is the case the naive
# "only reload what changed on disk" approach can't fix: reloading `leaf`
# alone updates leaf.VALUE, but mid.MID_VALUE was already computed and
# stashed away, and nothing recomputes it unless mid itself gets re-run
MID_VALUE = LEAF_VALUE * 10

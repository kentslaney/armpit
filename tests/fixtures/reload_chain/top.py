from mid import MID_VALUE

# the "module in between importing the modified one" from the bug report:
# `top` is two hops away from `leaf`, by way of `mid`
TOP_VALUE = MID_VALUE + 1

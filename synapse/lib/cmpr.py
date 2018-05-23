'''
A set of comparison functions that are used by types / filters.
'''

def eq(x, y):
    return x == y

def ne(x, y):
    return x != y

def ge(x, y):
    return x >= y

def le(x, y):
    return x <= y

def gt(x, y):
    return x > y

def lt(x, y):
    return x < y

# additionally, some comparator strings
# (which includes a bit of storm syntax knowledge)

cmprby = {
    '=': eq,
    '!=': ne,
    '>=': ge,
    '<=': le,
    '>': gt,
    '<': lt,
}

def get(by):
    return cmprby.get(by)

def cmpr(by, x, y):
    func = cmprby.get(by)
    return func(x, y)

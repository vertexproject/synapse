'''
Shared primitive routines for chopping up strings and values.
'''
def intstr(text):
    return int(text, 0)

def intrange(text):
    mins, maxs = text.split(':', 1)
    return intstr(mins), intstr(maxs)

def digits(text):
    return ''.join([c for c in text if c.isdigit()])

def times(text):
    '''
    One or more time stamps sep by - or ,
    Either a single time, or a time range split by -
    '''

def mergeRanges(x, y):
    '''
    Merge two ranges into one.
    '''
    minv = min(*x, *y)
    maxv = max(*x, *y)
    return (minv, maxv)

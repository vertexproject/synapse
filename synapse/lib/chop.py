'''
Shared primitive routines for chopping up strings into values.
'''
def intstr(text):
    return int(text, 0)

def intrange(text):
    mins, maxs = text.split(':', 1)
    return intstr(mins), intstr(maxs)

'''
A few utilities for dealing with intervals.
'''
import synapse.lib.time as s_time

def fold(*vals):
    '''
    Initialize a new (min,max) tuple interval from values.

    Args:
        *vals ([int,...]):  A list of values (or Nones)

    Returns:
        ((int,int)):    A (min,max) interval tuple or None

    '''
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return min(vals), max(vals)

def overlap(ival0, ival1):
    '''
    Determine if two interval tuples have overlap.

    Args:
        iv0 ((int,int)):    An interval tuple
        iv1 ((int,int));    An interval tuple

    Returns:
        (bool): True if the intervals overlap, otherwise False

    '''
    min0, max0 = ival0
    min1, max1 = ival1
    return max(0, min(max0, max1) - max(min0, min1)) > 0

def parsetime(text):
    '''
    Parse an interval time string and return a (min,max) tuple.

    Args:
        text (str): A time interval string

    Returns:
        ((int,int)):    A epoch millis epoch time string

    '''
    mins, maxs = text.split('-', 1)
    minv = s_time.parse(mins)
    maxv = s_time.parse(maxs, base=minv)
    return minv, maxv

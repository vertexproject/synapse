'''
A few utilities for dealing with intervals.
'''

def initIval(*vals):
    '''
    Initialize a new (min,max) tuple interval from values.

    Args:
        *vals ([int,...]):  A list of values (or Nones)

    Returns:
        ((int,int)):    A (min,max) interval tuple or None

    '''
    vals = [ v for v in vals if v is not None ]
    if not vals:
        return None
    return min(vals),max(vals)

class TimeIval:

    def __init__(self, *vals):

        self.mint = None
        self.maxt = None

        vals = [ v for v in vals if v is not None ]
        if vals:
            self.mint = min(vals)
            self.maxt = max(vals)

    def append(self, x):
        '''
        Append a value to the list of times used to calculate this interval.

        Args:
            x (int):    millisecond timestamp since epoch or None

        '''
        if x is None:
            return

        if self.mint == None or x < self.mint:
            self.mint = x

        if self.maxt == None or x > self.maxt:
            self.maxt = x

    def minmax(self):
        '''
        Return the min,max values for the time interval.
        '''
        return self.mint,self.maxt

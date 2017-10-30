import synapse.glob as s_glob

class CmpSet:
    '''
    The CmpSet class facilitates atomic compare and set.
    '''
    def __init__(self, valu):
        self.valu = valu

    def set(self, valu):
        '''
        Atomically set the valu and return change status.

        Args:
            valu (obj): The new value

        Returns:
            (bool): True if the value changed.
        '''
        with s_glob.lock:
            retn = self.valu != valu
            self.valu = valu
            return retn

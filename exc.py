'''
Exceptions used by for_lexicon, derived from synapse.
'''

class SynErr(Exception):

    def __init__(self, *args, **info):
        self.errinfo = info
        self.errname = self.__class__.__name__
        Exception.__init__(self, self._getExcMsg())

    def _getExcMsg(self):
        props = sorted(self.errinfo.items())
        displ = ' '.join(['%s=%r' % (p, v) for (p, v) in props])
        return '%s: %s' % (self.__class__.__name__, displ)

    def _setExcMesg(self):
        '''Should be called when self.errinfo is modified.'''
        self.args = (self._getExcMsg(),)

    def __setstate__(self, state):
        '''Pickle support.'''
        super(SynErr, self).__setstate__(state)
        self._setExcMesg()

    def items(self):
        return {k: v for k, v in self.errinfo.items()}

    def get(self, name, defv=None):
        '''
        Return a value from the errinfo dict.

        Example:

            try:
                foothing()
            except SynErr as e:
                blah = e.get('blah')

        '''
        return self.errinfo.get(name, defv)

    def set(self, name, valu):
        '''
        Set a value in the errinfo dict.
        '''
        self.errinfo[name] = valu
        self._setExcMesg()

    def setdefault(self, name, valu):
        '''
        Set a value in errinfo dict if it is not already set.
        '''
        if name in self.errinfo:
            return
        self.errinfo[name] = valu
        self._setExcMesg()

    def update(self, items: dict):
        '''Update multiple items in the errinfo dict at once.'''
        self.errinfo.update(items)
        self._setExcMesg()

class CryptoErr(SynErr):
    '''
    Raised when there is a for_lexicon.lib.crypto error.
    '''
    pass

class BadEccExchange(CryptoErr):
    ''' Raised when there is an issue doing a ECC Key Exchange '''
    pass

class BadDataValu(SynErr):
    '''Cannot process the data as intended.'''
    pass

class NotMsgpackSafe(SynErr):
    '''Raised when data cannot be serialized with msgpack.'''
    pass

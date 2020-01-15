class Changer:
    _changehandlers = []

    def __init__(self):
        self._chnghands = {}
        for event, func in self._changehandlers:
            self._chnghands[event] = func

    @classmethod
    def subscribe(cls, event):
        def decorator(func):
            cls._changehandlers.append((event, func))
            return func
        return decorator

    def onChange(self, evnt, func):
        '''
        Register a change handler
        '''
        prev = self.chnghands.setdefault(evnt, func)
        assert prev is None

    def offChange(self, evnt):
        prev = self.chnghands.pop(evnt)
        assert prev is not None

    async def _fireChange(self, mesg):
        '''
        Execute the change handler for the mesg
        '''
        return await self._chnghands[mesg[0]](self, mesg)

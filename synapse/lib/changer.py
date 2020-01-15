import synapse.common as s_common
import synapse.lib.base as s_base

class Changer(s_base.Base):
    _dechands = []  # type: ignore

    async def __anit__(self, iden=None, parent: 'Changer' = None):
        await s_base.Base.__anit__(self)
        self._chnghands = {}  # type: ignore
        self._chngkids = {}  # type: ignore

        root = self if parent is None else parent._chngroot

        if parent is not None:
            self._chngiden = s_common.guid() if iden is None else iden
            root._chngkids[self._chngiden] = self

            def onfini():
                prev = root._chngkids.pop(self._chngiden)
                assert prev is not None
            self.onfini(onfini)

        self._chngroot = root

        for event, func in self._dechands:
            self.onChange(event, func)

    @classmethod
    def onChng(cls, event):
        def decorator(func):
            cls._dechands.append((event, func))
            return func
        return decorator

    def onChange(self, evnt, func):
        '''
        Register a change handler
        '''
        assert evnt not in self._chnghands
        self._chnghands[evnt] = func

    def offChange(self, evnt):
        prev = self._chnghands.pop(evnt)
        assert prev is not None

    async def _fireChange(self, mesg):
        '''
        Execute the change handler for the mesg
        '''
        if isinstance(mesg[0], tuple):
            evnt, kididen = mesg[0]
            chgr = self._chngroot._chngkids[kididen]
            mesg = (evnt, mesg[1])
        else:
            chgr = self

        return await chgr._chnghands[mesg[0]](self, mesg)

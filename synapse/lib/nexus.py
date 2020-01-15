import synapse.common as s_common
import synapse.lib.base as s_base

class Nexus(s_base.Base):
    _dechands = []  # type: ignore

    async def __anit__(self, iden=None, parent: 'Nexus' = None):
        await s_base.Base.__anit__(self)
        self._nexshands = {}  # type: ignore
        self._nexskids = {}  # type: ignore

        root = self if parent is None else parent._nexsroot

        if parent is not None:
            self._nexsiden = s_common.guid() if iden is None else iden
            root._nexskids[self._nexsiden] = self

            def onfini():
                prev = root._nexskids.pop(self._nexsiden)
                assert prev is not None
            self.onfini(onfini)

        self._nexsroot = root

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
        assert evnt not in self._nexshands
        self._nexshands[evnt] = func

    def offChange(self, evnt):
        prev = self._nexshands.pop(evnt)
        assert prev is not None

    async def _fireChange(self, mesg):
        '''
        Execute the change handler for the mesg
        '''
        if isinstance(mesg[0], tuple):
            evnt, kididen = mesg[0]
            chgr = self._nexsroot._nexskids[kididen]
            mesg = (evnt, mesg[1])
        else:
            chgr = self

        return await chgr._nexshands[mesg[0]](self, mesg)

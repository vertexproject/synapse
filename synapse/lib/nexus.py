import synapse.lib.base as s_base

class NexusType(type):
    '''
    Metaclass that collects all methods in class with _regme prop into a class member called _nexsclsfuncs
    '''
    def __init__(cls, name, bases, attrs):
        # Start with my parents' definitions
        cls._nexsclsfuncs = sum((getattr(scls, '_nexsclsfuncs', []) for scls in bases), [])

        # Add my own definitions
        for meth in attrs.values():

            prop = getattr(meth, '_regme', None)
            if prop is not None:
                cls._nexsclsfuncs.append(prop)

class Nexus(s_base.Base, metaclass=NexusType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _nexsclsfuncs = []  # type:ignore

    async def __anit__(self, iden, parent: 'Nexus' = None):  # type: ignore
        await s_base.Base.__anit__(self)
        self._nexshands = {}  # type: ignore
        self._nexskids = {}  # type: ignore

        root = self if parent is None else parent._nexsroot  # type:ignore

        if parent:
            self._nexsiden = iden
            root._nexskids[self._nexsiden] = self

            def onfini():
                prev = root._nexskids.pop(self._nexsiden)
                assert prev is not None
            self.onfini(onfini)

        self._nexsroot = root

        for event, func in self._nexsclsfuncs:  # type: ignore
            self._nexshands[event] = func

    @classmethod
    def onPush(cls, event: str):
        '''
        Decorator that registers a method to be a handler for a named event
        '''
        def decorator(func):
            func._regme = (event, func)
            return func

        return decorator

    async def _push(self, event, parms, iden=None):
        '''
        Execute the change handler for the mesg

        Note:
            This method is considered 'protected', in that it should not be called from something other than self.
        '''
        if self._nexsroot is not self:  # I'm below the root
            if iden is None:
                iden = self._nexsiden
            # We call the root's method, as he might have overriden _push
            return await self._nexsroot._push(event, parms, iden)

        # I'm the root
        nexus = self if iden is None else self._nexskids[iden]
        return await nexus._nexshands[event](nexus, *parms)

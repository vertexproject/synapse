import functools

import synapse.common as s_common
import synapse.lib.base as s_base

class NexusType(type):
    '''
    Metaclass that collects all methods in class with _regme prop into a class member called _nexsclsfuncs
    '''
    def __init__(cls, name, bases, attrs):
        cls._nexsclsfuncs = []
        for meth in attrs.values():

            prop = getattr(meth, '_regme', None)
            if prop is not None:
                cls._nexsclsfuncs.append(prop)

class Nexus(s_base.Base, metaclass=NexusType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _nexsclsfuncs = []  # type:ignore

    async def __anit__(self, iden, parent: 'Nexus' = None):
        await s_base.Base.__anit__(self)
        self._nexshands = {}  # type: ignore
        self._nexskids = {}  # type: ignore

        root = self if parent is None else parent._nexsroot  # type:ignore

        if parent is not None:
            self._nexsiden = iden
            root._nexskids[self._nexsiden] = self

            def onfini():
                prev = root._nexskids.pop(self._nexsiden)
                assert prev is not None
            self.onfini(onfini)

        self._nexsroot = root

        for event, func in self._nexsclsfuncs:  # type: ignore
            #     assert evnt not in self._nexshands
            #     self._nexshands[evnt] = func
            assert event not in self._nexshands
            self._nexshands[event] = func

        # Fill in any unhandled-by-this-class inherited handlers
        for scls in self.__class__.__bases__:
            rfuncs = getattr(scls, '_nexsclsfuncs', None)
            if not rfuncs:
                continue
            for event, func in rfuncs:
                self._nexshands.setdefault(event, func)

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
            This method should be considered 'protected', in that it should not be called from another object.
        '''
        if iden is None and self is not self._nexsroot:
            iden = self._nexsiden

        nexus = self if iden is None else self._nexsroot._nexskids[iden]
        return await nexus._nexshands[event](nexus, *parms)

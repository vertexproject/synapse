import functools

import synapse.common as s_common
import synapse.lib.base as s_base

class NexusType(type):
    '''
    Metaclass that collects all methods in class with _regme prop into a class member called _regfuncs
    '''
    def __init__(cls, name, bases, attrs):
        cls._regfuncs = []
        for meth in attrs.values():

            prop = getattr(meth, '_regme', None)
            if prop is not None:
                cls._regfuncs.append(prop)

class Nexus(s_base.Base, metaclass=NexusType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _regfuncs = []  # type:ignore

    async def __anit__(self, iden=None, parent: 'Nexus' = None):
        await s_base.Base.__anit__(self)
        self._nexshands = {}  # type: ignore
        self._nexskids = {}  # type: ignore

        root = self if parent is None else parent._nexsroot  # type:ignore

        if parent is not None:
            self._nexsiden = s_common.guid() if iden is None else iden
            root._nexskids[self._nexsiden] = self

            def onfini():
                prev = root._nexskids.pop(self._nexsiden)
                assert prev is not None
            self.onfini(onfini)

        self._nexsroot = root

        for event, func in self._regfuncs:  # type: ignore
            self.onChange(event, functools.partial(func, self))

        # Fill in any unhandled-by-this-class inherited handlers
        for scls in self.__class__.__bases__:
            rfuncs = getattr(scls, '_regfuncs', None)
            if not rfuncs:
                continue
            for event, func in rfuncs:
                if event not in self._nexshands:
                    self.onChange(event, functools.partial(func, self))

    @classmethod
    def onChng(cls, event: str):
        '''
        Decorator that registers a method to be a handler for a named event
        '''
        def decorator(func):
            func._regme = (event, func)
            return func

        return decorator

    def onChange(self, evnt, func):
        '''
        Register a change handler
        '''
        assert evnt not in self._nexshands
        self._nexshands[evnt] = func

    # def offChange(self, evnt):
    #     prev = self._nexshands.pop(evnt)
    #     assert prev is not None

    async def _fireChange(self, event, parms, iden=None):
        '''
        Execute the change handler for the mesg
        '''
        if iden is None and self is not self._nexsroot:
            iden = self._nexsiden

        nexus = self if iden is None else self._nexsroot._nexskids[iden]
        return await nexus._nexshands[event](*parms)

from typing import List, Dict, Any

import synapse.lib.base as s_base

class RegMethType(type):
    '''
    Metaclass that collects all methods in class with _regme prop into a class member called _regclsfuncs
    '''
    def __init__(cls, name: str, bases: List[type], attrs: Dict[str, Any]):
        # Start with my parents' definitions
        cls._regclsfuncs = sum((getattr(scls, '_regclsfuncs', []) for scls in bases), [])

        # Add my own definitions
        for meth in attrs.values():

            prop = getattr(meth, '_regme', None)
            if prop is not None:
                cls._regclsfuncs.append(prop)

class NexsRoot(s_base.Base):
    async def __anit__(self):
        await s_base.Base.__anit__(self)
        self._nexskids = {}

    async def issue(self, nexsiden: str, event: str, args: Any, kwargs: Any):
        # Log the message here
        nexus = self._nexskids[nexsiden]
        return await nexus._nexshands[event](nexus, *args, **kwargs)

    async def eat(self, nexsiden: str, event: str, args: List[Any], kwargs: Dict[str, Any]):
        '''
        Called from an external API
        '''
        nexus = self._nexskids[nexsiden]
        return await nexus._push(event, *args, **kwargs)

class Pusher(s_base.Base, metaclass=RegMethType):
    '''
    A mixin-class to manage distributing changes where one might plug in mirroring or consensus protocols
    '''
    _regclsfuncs = []  # type:ignore

    # FIXME:  parent -> nexsroot
    async def __anit__(self, iden: str, nexsroot: NexsRoot = None):  # type: ignore
        await s_base.Base.__anit__(self)
        self._nexshands = {}  # type: ignore

        self._nexsiden = iden

        if nexsroot:
            assert iden
            nexsroot._nexskids[iden] = self

            def onfini():
                prev = nexsroot._nexskids.pop(iden, None)
                # FIXME remove
                if prev is None:
                    breakpoint()
                assert prev is not None
            self.onfini(onfini)

        self._nexsroot = nexsroot

        for event, func in self._regclsfuncs:  # type: ignore
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

    async def _push(self, event: str, *args: List[Any], **kwargs: Dict[str, Any]):
        '''
        Execute the change handler for the mesg

        Note:
            This method is considered 'protected', in that it should not be called from something other than self.
        '''
        nexsiden = self._nexsiden
        if self._nexsroot:  # I'm below the root
            return await self._nexsroot.issue(nexsiden, event, args, kwargs)

        # There's not change dist
        return await self._nexshands[event](self, *args, **kwargs)

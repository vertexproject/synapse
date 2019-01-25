import asyncio

from typing import Any, Dict, List, Tuple

class EditAtom:
    def __init__(self, allbldgbuids):
        self.mybldgbuids = {}  # buid -> node
        self.otherbldgbuids = set()
        self.doneevent = asyncio.Event()
        self.sops: List[Tuple[str, Tuple[bytes, str, str, Dict[str, Any]]]] = []
        self.allbldgbuids = allbldgbuids # buid -> (Node, Event)
        self.notified = False
        self.npvs = [] # List of tuple(Node, prop, val)

    def __enter__(self):
        return self

    def getNodeBeingMade(self, buid):
        '''
        Return a node if it is currently being made, mark as a dependency, else None if none found
        '''
        valu = self.allbldgbuids.get(buid)
        if valu is None:
            return None
        if buid not in self.mybldgbuids:
            self.otherbldgbuids.add(buid)
        return valu[0]

    def addNode(self, node):
        '''
        Update the shared map with my in-construction nodes
        '''
        self.mybldgbuids[node.buid] = node
        self.allbldgbuids[node.buid] = (node, self.doneevent)

    async def rendevous(self):
        '''
        Wait until all my adjacent editatoms are also at this point
        '''
        self._notifyDone()
        await self._wait()

    def _notifyDone(self):
        '''
        Allow any other editatoms waiting on this to complete to resume
        '''
        if self.notified:
            return

        self.doneevent.set()

        for buid in self.mybldgbuids:
            del self.allbldgbuids[buid]

        self.notified = True

    async def _wait(self):
        '''
        Wait on the other editatoms who are constructing nodes my new nodes refer to
        '''
        for buid in self.otherbldgbuids:
            _, evnt = self.allbldgbuids.get(buid)
            if buid is None:
                continue
            await evnt.wait()

    def __exit__(self, exc, cls, tb):
        self._notifyDone()

    async def commit(self, snap):
        for node, prop, _, valu in self.npvs:
            node.props[prop.name] = valu

        await snap.stor(self.sops)

        for node in self.mybldgbuids.values():
            snap.core.pokeFormCount(node.form.name, 1)
            snap.buidcache.put(node.buid, node)

        await self.rendevous()

        for node in self.mybldgbuids.values():
            await snap.splice('node:add', ndef=node.ndef)
            await node.form.wasAdded(node)

        # fire all his prop sets
        for name, prop, oldv, valu in self.npvs:
            await snap.splice('prop:set', ndef=node.ndef, prop=prop.name, valu=valu, oldv=oldv)
            await prop.wasSet(node, oldv)

            if prop.univ:
                univ = snap.model.prop(prop.univ)
                await univ.wasSet(self, oldv)

            await snap.core.triggers.run(node, 'prop:set', info={'prop': prop.full})

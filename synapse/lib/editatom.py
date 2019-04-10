import asyncio

from typing import Any, Dict, List, Tuple

class EditAtom:
    '''
    A simple utility class to track all the changes for adding a node or setting a property before committing them all
    at once.
    '''
    def __init__(self, allbldgbuids):
        '''
        Args:
            allbldgbuids (Dict[bytes, Node]): a dict that should be shared among all instances of this class for a
            particular cortex.
        '''
        self.mybldgbuids = {}  # buid -> node
        self.otherbldgbuids = set()
        self.doneevent = asyncio.Event()
        self.sops: List[Tuple[str, Tuple[bytes, str, str, Dict[str, Any]]]] = []
        self.allbldgbuids = allbldgbuids # buid -> (Node, Event)
        self.notified = False
        self.npvs = [] # List of tuple(Node, prop, val)

    def __enter__(self):
        '''
        Implement the context manager convention
        '''
        return self

    def getNodeBeingMade(self, buid):
        '''
        Return a node if it is currently being made, mark as a dependency, else None if none found
        '''
        nodeevnt = self.allbldgbuids.get(buid)
        if nodeevnt is None:
            return None
        if buid not in self.mybldgbuids:
            self.otherbldgbuids.add(buid)
        return nodeevnt[0]

    def addNode(self, node):
        '''
        Update the shared map with my in-construction node
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
        Allow any other editatoms waiting on me to complete to resume
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
            nodeevnt = self.allbldgbuids.get(buid)
            if nodeevnt is None:
                continue
            await nodeevnt[1].wait()

    def __exit__(self, exc, cls, tb):
        '''
        Regardless of success, wake up any waiters and clean myself up from shared dict
        '''
        self._notifyDone()

    async def commit(self, snap):
        '''
        Push the recorded changes to disk, notify all the listeners
        '''
        if not self.npvs:  # nothing to do
            return

        for node, prop, _, valu in self.npvs:
            node.props[prop.name] = valu
            node.proplayr[prop.name] = snap.wlyr

        splices = [snap.splice('node:add', ndef=node.ndef) for node in self.mybldgbuids.values()]
        for node, prop, oldv, valu in self.npvs:
            info = {'ndef': node.ndef, 'prop': prop.name, 'valu': valu}
            if oldv is not None:
                info['oldv'] = oldv
            splices.append(snap.splice('prop:set', **info))

        await snap.stor(self.sops, splices)

        for node in self.mybldgbuids.values():
            snap.core.pokeFormCount(node.form.name, 1)
            snap.buidcache.append(node)
            snap.livenodes[node.buid] = node

        await self.rendevous()

        for node in self.mybldgbuids.values():
            await node.form.wasAdded(node)

        # fire all his prop sets
        for node, prop, oldv, valu in self.npvs:
            await prop.wasSet(node, oldv)

            if prop.univ:
                univ = snap.model.prop(prop.univ)
                await univ.wasSet(node, oldv)

        # Finally, fire all the triggers
        for node, prop, oldv, _ in self.npvs:
            await snap.core.triggers.runPropSet(node, prop, oldv)

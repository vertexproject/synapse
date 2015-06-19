import time
import msgpack
import collections

import Crypto.PublicKey.RSA as RSA
import Crypto.Cipher.PKCS1_v1_5 as PKCS15

#import synapse.common as s_common
#import synapse.socket as s_socket
import synapse.threads as s_threads
import synapse.service as s_service

from synapse.common import *
from synapse.eventbus import EventBus
from synapse.statemach import StateMachine, keepstate

class NeuError(Exception):pass
class NoSuchPeer(NeuError):pass

class Neuron(s_service.Service):
    '''
    A Neuron facilitates distributed "mesh" computing through peer routing.

    Each Neuron in a mesh tracks routes and link status messages announced
    by the other neurons and keeps a complete map of the links between each.

    '''
    def initServiceLocals(self):

        self.ident = None
        self.sched = s_threads.Sched()

        # this is for transient / runtime info
        self.peersocks = collections.defaultdict(set)
        self.peerlinks = collections.defaultdict(set)
        self.routecache = {}

        # persistant data in these...
        self.neuinfo = {}
        self.peerinfo = collections.defaultdict(dict)

        #self.neuinfo.setdefault('rsamaster',None)   # do we know an RSA master key? ( CA stylez )

        self.databus = EventBus()     # for app layer mesgs routed to us
        self.peerbus = EventBus()     # for neu layer mesgs recvd from peers

        self.peerbus.synOn('neu:syn', self._onNeuSyn )
        self.peerbus.synOn('neu:data', self._onNeuData )

        # check if we're brand new...
        if self.neuinfo.get('ident') == None:
            # making a shiney new neuron!
            self.setNeuInfo('ident', guid())

        if self.neuinfo.get('rsakey') == None:
            rsakey = RSA.generate(2048)
            keytup = ( rsakey.n, rsakey.e, rsakey.d )
            self.setNeuInfo('rsakey',keytup)

        # cache the crypto key object
        keytup = self.getNeuInfo('rsakey')
        self.rsakey = RSA.construct(keytup)
        self.pkcs15 = PKCS15.new( self.rsakey )

    def _getPeerRoute(self, peerid):
        '''
        Calculate and return the shortest known path to peer.
        '''
        route = self.routecache.get(peerid)
        if route != None:
            return route

        done = set()
        todo = collections.deque(( [self.ident,], ))

        # breadth first search...
        while todo:

            route = todo.popleft()
            lasthop = route[-1]

            if lasthop in done:
                continue

            done.add(lasthop)

            for n2 in self.peerlinks[lasthop]:

                if n2 == peerid:
                    route.append(n2)
                    self.routecache[peerid] = route
                    return route

                if n2 in done:
                    continue

                todo.append( route + [n2] )

    def _addPeerLink(self, src, dst):
        self.peerlinks[src].add(dst)

    def _delPeerLink(self, src, dst):
        self.peerlinks[src].remove(dst)

    def _hasPeerLink(self, src, dst):
        return dst in self.peerlinks[src]

    def _getRouteSock(self, peerid):
        '''
        Return the best socket to route a mesg to by peer id.

        Example:

            sock = neu._getRouteSock( peerid )

        '''
        for sock in self.peersocks[peerid]:
            return sock

    #def _neuRouteMesg(self, sock, mesg):
        #self.peerbus.synFire(msg[0], sock, mesg)

    def _onNeuSyn(self, sock, mesg):
        peer = mesg[1].get('peer')

        # SEND OUT ANNOUNCEMENT!

        sid = sock.getSockId()
        def poppeer():
            self.peersocks[peer].remove(sid,None)

        self.peersocks[peer].add(sock)

        for src,dst in mesg[1].get('peerlinks'):
            self._addPeerLink(src,dst)

    def _onNeuData(self, sock, mesg):
        '''
        A Neuron "data" message which should be routed.

        ('neu:data', {
            'hop':<int>, # index into route
            'route':[srcpeer, ... ,dstpeer] # neu:data is source routed
            'mesg':<datamesg>,
        })

        '''
        hop = mesg[1].get('hop') + 1
        route = mesg[1].get('route')

        # update the hop index.
        mesg[1]['hop'] = hop

        nexthop = route[hop]
        if nexthop == self.ident:
            self.databus.synFire(mesg[0],sock=sock,mesg=mesg)
            return

        fwdsock = self._getRouteSock(nexthop)
        if fwdsock == None:
            return self._schedMesgRetrans(nexthop, mesg)

        if not fwdsock.sendobj(mesg):
            return self._schedMesgRetrans(nexthop, mesg)

    def _schedMesgRetrans(self, nexthop, mesg, maxtries=10):
        tries = 0
        def runretrans():
            if mesg[1].get('sent'):
                return

            fwdsock = self._getRouteSock(nexthop)
            if fwdsock != None:
                if fwdsock.sendobj(mesg):
                    return

            tries += 1
            if tries < maxtries:
                self.sched.synIn(0.2, runretrans)
                return

            # ok, we're out.  try to tell the sender.
            # FIXME SEND DEST UNREACH

        self.sched.synIn( 0.2, runretrans )

    #@keepstate
    def setPeerInfo(self, peerid, prop, valu):
        '''
        Set a property about a peer.

        Example:

            neu.setPeerInfo(peerid,'foo',30)

        '''
        self.peerinfo[peerid][prop] = valu

    def getPeerInfo(self, peerid, prop):
        '''
        Return a property about a peer by id.

        Example:

            neu.getPeerInfo(peerid,'foo')

        '''
        # FIXME what do we do with invalid peerid?
        info = self.peerinfo.get(peerid)
        if info == None:
            raise NoSuchPeer(peerid)
        return info.get(prop)

    #@keepstate
    def setNeuInfo(self, prop, valu):
        '''
        Set a property of this Neuron.

        Example:

            neu.setNeuInfo('foo',30)

        '''
        self.neuinfo[prop] = valu
        #self.synFire('neu:prop',prop,valu)
        #self.synFire('neu:prop:%s' % prop,valu)

    def getNeuInfo(self, prop):
        '''
        Get a property of this Neuron.

        Example:

            neu.getNeuInfo('foo')

        '''
        return self.neuinfo.get(prop)

    @keepstate
    def delPeerById(self, peerid):
        '''
        Delete a peer and all options associated with it.

        Example:

            neu.delPeerById(peerid)

        '''
        self.peerinfo.pop(peerid,None)

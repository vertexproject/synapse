import time
import msgpack
import collections

import synapse.common as s_common
import synapse.socket as s_socket

from synapse.threads import firethread
from synapse.dispatch import Dispatcher
from synapse.statemach import StateMachine, keepstate

class NeuError(Exception):pass
class NoSuchPeer(NeuError):pass
class NoSuchApiKey(NeuError):pass

class Neuron(s_socket.SocketPool):
    '''
    FIXME this is still in brainstorm/thrash mode... :)
    '''
    def __init__(self, statefd=None):

        self.ident = None
        self.peers = {}     # runtime peer info

        # persistant data in these...
        self.neuinfo = {}

        self.peerinfo = collections.defaultdict(dict)
        self.apikeyinfo = collections.defaultdict(dict)

        # must set up locals before SocketPool (StateMachine)...
        s_sock.SocketPool(statefd=statefd)

        # check if we're brand new...
        if self.neuinfo.get('ident') == None:
            # making a shiney new neuron!
            self.setNeuInfo('ident', s_common.guid())

        size = self.neuinfo.get('sockpool')

        self.sockpool = s_socket.SocketPool(pool=size)
        self.sockpool.synOn('sockmesg', self._neuRouteMesg)

        # are there any peers we're supposed to link to?
        #for peerid in self.peerinfo.keys():
            #self.firePeerLink(peerid)

    def _neuRouteMesg(self, sock, msg):
        print('got a message!')

    def firePeerLink(self, peerid):
        '''
        A peer "link" is a connection we must establish and maintain.

        Example:

            neu.firePeerLink(peerid)
        '''
        #self.threads.append( self._runPeerLink(peerid) )

    @firethread
    def _runPeerLink(self, peerid):
        while not self.isfini:
            link = self.getPeerInfo(peerid,'link')
            meth = self.linkprotos.get( link[0] )
            if meth == None:
                time.sleep(1) # FIXME event
                continue

            meth(link)

    def _linkTcpProto(self, link):
        host = link[1].get('host')
        port = link[1].get('port')

        sock = s_socket.connect((host,port))
        if not sock:
            return False

        sock.setSockInfo('peer',True)

    @keepstate
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

    @keepstate
    def setNeuInfo(self, prop, valu):
        '''
        Set a property of this Neuron.

        Example:

            neu.setNeuInfo('foo',30)

        '''
        self.neuinfo[prop] = valu
        self.synFireHup()

    def getNeuInfo(self, prop):
        '''
        Get a property of this Neuron.

        Example:

            neu.getNeuInfo('foo')

        '''
        return self.neuinfo.get(prop)

    @keepstate
    def setApiKeyInfo(self, apikey, prop, valu):
        '''
        Set a configuration property for an API key.


        Example:

            neu.setApiKeyInfo(apikey,'foo',30)

        '''
        self.apikeyinfo[apikey][prop] = valu

    def getApiKeyInfo(self, apikey, prop):
        '''
        Get an API key configuration option.

        Example:

            neu.getApiConfigInfo(apikey,'foo')

        '''
        info = self.apikeyinfo.get(apikey)
        if info == None:
            raise NoSuchApiKey(apikey)
        return info.get(prop)

    @keepstate
    def delApiKey(self, apikey):
        '''
        Delete an API key and all options associated with it.

        Example:

            neu.delApiKey(apikey)

        '''
        self.apikeyinfo.pop(apikey,None)

    def synFireHup(self):
        self.synFire('hup')

    @keepstate
    def delPeerById(self, peerid):
        '''
        Delete a peer and all options associated with it.

        Example:

            neu.delPeerById(peerid)

        '''
        self.peerinfo.pop(peerid,None)

    def initPeerKey(self, peerid):
        '''
        Initialize and return a new key for comms with peerid.

        Example:

            peerkey = neu.initPeerKey(peerid)
            # now tell the other guy about they key :)

        '''
        peerkey = guid()
        self.setKeyForPeer(peerid,peerkey)
        return key

    def initApiKey(self, name):
        '''
        Initialize a new API key with the given name.

        Example:

            neu.initApiKey('visi@yourgirlfriends.computer')

        '''
        apikey = s_common.guid()
        self.setApiKeyInfo(apikey,'name',name)
        return apikey


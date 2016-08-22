import json
import time
import logging
import msgpack
import traceback
import collections

import synapse.link as s_link
import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.tags as s_tags
import synapse.lib.sched as s_sched
import synapse.lib.cache as s_cache
import synapse.lib.socket as s_socket

from synapse.common import *
from synapse.lib.threads import firethread

import synapse.impulse as s_impulse
from synapse.eventbus import EventBus

logger = logging.getLogger(__name__)

# FIXME maybe should go in neuron link protocol / relay?
class NeuSock(s_socket.Socket):

    def __init__(self, neur, dest):
        s_socket.Socket.__init__(self, None)
        self.neur = neur
        self.dest = dest

    def tx(self, mesg):
        self.neur.route( self.dest, mesg, dsid=self.dsid)

class Neuron(s_daemon.Daemon):

    '''
    Neurons implement a peer-to-peer network mesh using any
    available synapse link protocol.  A neuron mesh provides service
    discovery and RMI transport to allow clients to reach services
    and APIs via the application layer mesh.
    '''

    def __init__(self, core=None, pool=None):

        s_daemon.Daemon.__init__(self, core=core, pool=pool)

        self.sched = s_sched.Sched()

        self.core.addTufoForm('neuron')

        #self.core.addTufoProp('neuron','name')
        #self.core.addTufoProp('neuron','super',ptype='int',defval=0)
        #self.core.addTufoProp('neuron','usepki', ptype='bool', defval=0)

        self.neur = self.core.formTufoByProp('neuron','self')
        self.iden = self.neur[0]

        self.peers = {}  # <peer>:<sock>
        self.routes = {} # <dest>:[ (dist,peer), ... ]

        #self.mesh = {}
        #self.peers = {}

        #self.mesh['certs'] = {}
        #self.mesh['links'] = {}

        #self.mesh['peers'] = { self.iden:self.neur }

        #self.sockbyfrom = s_cache.Cache(maxtime=120)
        #self.sockbyfrom.setOnMiss( self._getFakeSock )

        #self.links = collections.defaultdict(set)
#
        #self.linkpaths = s_cache.Cache(maxtime=30)
        #self.linkpaths.setOnMiss( self._getLinkPath )

        self.setMesgFunc('peer:syn', self._onPeerSynMesg )
        self.setMesgFunc('peer:synack', self._onPeerSynAckMesg )
        self.setMesgFunc('peer:fin', self._onPeerFinMesg )      # gracefully shut down

        self.setMesgFunc('peer:data', self._onPeerDataMesg)
        self.setMesgFunc('peer:route', self._onPeerLinkMesg)    # route change information

        #self.setMesgFunc('peer:link:init', self._onPeerLinkInitMesg )

        #self.setMesgFunc('neu:peer:chal', self._onNeuPeerChal )
        #self.setMesgFunc('neu:peer:resp', self._onNeuPeerResp )

        #self.setMesgFunc('neu:data', self._onNeuDataMesg )
        #self.setMesgFunc('neu:storm', self._onNeuStormMesg )

        self.on('neu:link:init', self._onNeuLinkInit)
        self.on('neu:link:fini', self._onNeuLinkFini)

        self.share('neuron',self)

        self.hasopt = {}

        # fire any persistent neuron listeners
        for url in self.core.getTufoList(self.neur, 'listen'):
            try:
                self.listen(url)
                self.hasopt[ ('listen',url) ] = True
            except Exception as e:
                logger.error('neu listen: %s', e)

        # spin up any persistent neuron connections
        for url in self.core.getTufoList(self.neur, 'connect'):
            try:
                self.connect(url)
                self.hasopt[ ('connect',url) ] = True
            except Exception as e:
                logger.error('neu connect: %s', e)

        # load any persistent shared objects
        for jsval in self.core.getTufoList(self.neur, 'shared'):

            try:
                info = json.loads(v)

                name = info.get('name')
                task = info.get('task')
                tags = info.get('tags',())

                item = s_dyndeps.runDynTask(task)

                self.share(name,item,tags=tags)

            except Exception as e:
                logger.error('neu share: %s', e)

    def setNeuProp(self, prop, valu):
        '''
        Set a property for this neuron.

        Example:

            neu.setNeuProp('name','woot0')

        '''
        self.core.setTufoProp(self.neur,prop,valu)
        # FIXME AUTH / PERMS
        # FIXME send peer update

    def getNeuProp(self, prop):
        '''
        Return a property for this neuron.
        '''
        return self.neur[1].get(prop)

    #def addShareTask(self, name, task, tags=()):
        #'''
        #Add a 'task' tufo to initialize during Neuron startup.
        #'''

    #def addNeuShare(self, name, task, tags=()):
        #'''
        #Add a shared object to the neuron

        #Example:

            #task = ('synapse.cortex.openurl', ('ram:///',), {})

            #neu.addNeuShare('hehe', task, tags=('foo.bar.baz',))

        #'''
        #item = s_dyndeps.runDynTask(task)
        #self.share(name,item,tags=tags)

        #jsinfo = dict(name=name, task=task, tags=tags)
        #self.core.addTufoList(self.neur,'shared', json.dumps(jsinfo) )

    #def addNeuListen(self, url):
        #'''
        #Add a link listen url to the neuron

        #Example:

            #neu.addNeuListen('tcp://0.0.0.0:9999')

        #'''
        #if self.hasopt.get(('listen',url)):
            #raise DupOpt('listen: %s' % url)
#
        #self.listen(url)
        #self.core.addTufoList(self.neur,'listen',url)

    #def addNeuConnect(self, url):
        ##'''
        #Add a link connect url to the neuron

        #Example:

            #neu.addNeuConnect('tcp://mesh.kenshoto.com:9999')

        #'''
        #if self.hasopt.get(('connect',url)):
            #raise DupOpt('connect: %s' % url)

        #self.connect(url)
        #self.core.addTufoList(self.neur,'connect',url)

    def _getFakeSock(self, idensid):
        iden,sid = idensid
        return NeuSock(self,iden,sid)

    def _sendPeerSyn(self, sock):

        # only do this once per socket..
        if sock.get('peer:chal'):
            return

        # generate and save a challenge blob for the peer
        chal = os.urandom(16)
        sock.set('peer:chal', chal)

        # transmit our peer:syn message with challenge blob
        sock.tx( tufo('peer:syn', chal=chal) )

    def _onPeerSynMesg(self, sock, mesg):
        '''
        Handle peer:syn message to become a neuron peer.
        '''
        sign = None
        chal = mesg[1].get('chal')

        if chal != None:
            sign = self.pki.genByteSign(self.iden, chal)

        cert = self.pki.getTokenCert(self.iden)
        sock.tx(tufo('peer:synack', iden=self.iden, mesh=self.mesh, cert=cert, sign=sign))

        # this will not send if we've already done so...
        self._sendPeerSyn(sock)

    def _onPeerSynAckMesg(self, sock, mesg):
        '''
        Handle a peer:synack hello from a peer we connected to.
        '''
        chal = sock.get('peer:chal')
        if chal == None:
            # we didn't send a chal... newp!
            return

        iden = mesg[1].get('iden')
        mesh = mesg[1].get('mesh')
        sign = mesg[1].get('sign')
        cert = mesg[1].get('cert')

        if cert != None:
            self.pki.loadCertToken(cert, save=True)

        if self.neur[1].get('neuron:usepki'):
            if not self.pki.isValidSign(iden, sign, chal):
                return

        self.mesh['certs'][iden] = cert

        # Inform the requestor that we have accepted them as a peer
        self._syncMeshDict(mesh)
        self._setPeerSock(iden,sock)

        # this must be after mesh dict updates!
        self._genMeshLinkStorm(sock)

    def _onPeerLinkInitMesg(self, sock, mesg):
        # peer:syn->peer:synack->peer:link:init

        # the peer:link message confirms that the sender
        # has accepted us as a peer so we may begin sending
        # storm/data messages.

        sock.set('peer:link',True)
        self._genMeshLinkStorm(sock)

    def _syncMeshDict(self, mesh):
        '''
        Ingest the mesh dict from a peer
        '''
        for iden,cert in mesh.get('certs',{}).items():
            if cert != None:
                self.pki.loadCertToken(cert, save=False)

        for iden,peer in mesh.get('peers',{}).items():
            if self.mesh['peers'].get(iden) == None:
                self.mesh['peers'][iden] = peer

        for (iden1,iden2),info in mesh.get('links',{}).items():
            self.addPathLink(iden1,iden2,**info)

    def _genMeshLinkStorm(self, sock):
        # check if the sock has been mutually peer'd yet
        # and possibly make the storm() announce if so.

        # do we think he's a peer yet?
        iden = sock.get('peer:peer')
        if iden == None:
            return False

        # does he think we're a peer yet?
        if not sock.get('peer:link'):
            return False

        mesh = self.getMeshDict()
        cert = self.pki.getTokenCert(self.iden)

        self.storm('neu:link:init', link=(self.iden,iden), cert=cert, mesh=mesh)

    def _setPeerSock(self, iden, sock):
        '''
        Record that a peer is on the other end of sock.
        '''
        # we can use this to ensure messages are from peer socks
        self.peers[iden] = sock
        sock.set('peer:peer',iden)

        def onfini():
            # FIXME peer lock and check if it's our sock?
            self.peers.pop(iden,None)
            self.storm('neu:link:fini', link=(self.iden,iden))

        sock.onfini(onfini)

        sock.tx( tufo('peer:link:init') )
        #self.storm('neu:link:init', link=(self.iden,iden))

    def _onNeuDataMesg(self, sock, mesg):
        '''
        Handle neu:data message ( most likely routing )
        '''
        # This message is only valid from peer socks
        if not sock.get('peer:peer'):
            return

        off = mesg[1].get('off') + 1
        path = mesg[1].get('path')

        # If we're not there yet, route it along...
        if len(path) > off:
            dest = path[off]
            mesg[1]['off'] = off

            peer = self.peers.get(dest)
            if peer == None:
                # FIXME SEND ERROR BACK
                return

            peer.tx( mesg )
            return

        # we are the final hop
        byts = mesg[1].get('byts')
        newm = msgunpack(byts)

        jid = mesg[1].get('jid')
        ssid = mesg[1].get('ssid')
        dsid = mesg[1].get('dsid')

        if dsid != None:
            sess = self.cura.getSessBySid(dsid)
            if sess == None: # the session is gone/expired...
                # FIXME SEND ERROR BACK
                return

            sess.dist(newm)
            return

        ssid = mesg[1].get('ssid')
        sock = self.sockbyfrom.get( (path[0],ssid) )

        self._runLinkSockMesg( tufo('link:sock:mesg', sock=sock, mesg=newm) )

    #def getPeerTufo(self):
        #'''
        #Return the "peer tufo" for this neuron.

        #Example:

            #peer = neu.getPeerTufo()

        #'''
        #return self.neur

    def getMeshDict(self):
        '''
        Return this neurons knowledge of the state of the mesh.

        Example:

            mesh = neu.getMeshDict()

        '''
        return self.mesh

    def getModelDict(self):
        '''
        Return the DataModel() dict for this neuron's cortex.

        Example:

            moddef = neu.getModelDict()

        '''
        return self.core.getModelDict()

    def ping(self):
        '''
        Retrieve vital stats for a neuron ( and gauge RTT ).
        '''
        return {'iden':self.iden}

    def getPathTrees(self):
        '''
        Return a list of trees for shortest path broadcast.
        '''
        done = set([self.iden])
        trees = [ (i,[]) for i in self.links[self.iden] ]

        todo = list(trees)
        while todo:
            node = todo.pop()
            for iden in list(self.links[ node[0] ]):
                if iden in done:
                    continue

                done.add(iden)

                newn = (iden,[])
                todo.append(newn)
                node[1].append(newn)

        return trees

    def getPathLinks(self):
        '''
        Return a list of (id1,id2) tuples for each known link.
        '''
        links = []
        for iden,peers in self.links.items():
            links.extend( [ (iden,p) for p in peers ] )
        return links

    def addPathLink(self, iden1, iden2, **info):
        '''
        Add a link to the known paths.
        '''
        self.links[iden1].add(iden2)
        self.mesh['links'][ (iden1,iden2) ] = info

    def delPathLink(self, iden1, iden2):
        '''
        Delete a known mesh path link.
        '''
        self.links[iden1].discard(iden2)
        self.mesh['links'].pop( (iden1,iden2), None )

    def addPathLinks(self, links):
        '''
        Add multiple (id1,id2) link tuples.
        '''
        [ self.addPathLink(iden1,iden2) for (iden1,iden2) in links ]

    def getLinkPath(self, iden1, iden2):
        '''
        Find the shortest path from iden1 to iden2
        '''
        return self.linkpaths.get( (iden1,iden2) )

    def _getLinkPath(self, identup ):
        iden1, iden2 = identup

        todo = [ [iden1] ]

        done = set()
        while todo:
            path = todo.pop()
            for iden in self.links[ path[-1] ]:
                if iden in done:
                    continue

                done.add(iden)
                if iden == iden2:
                    path.append(iden)
                    return path

                todo.append( path + [ iden ] )

    def connect(self, url, **opts):
        '''
        Connect to a peer neuron

        This will attempt to bring up a permanent connection
        and reconnect if it is torn down.
        '''
        if self.isfini:
            return

        link = s_link.chopLinkUrl(url)
        link[1].update(opts)

        relay = s_link.getLinkRelay(link)

        sock = relay.connect()
        if sock == None:
            self.sched.insec( 1, self.connect, url, **opts )
            return None

        self.runPlexSock(sock)

        sock.tx( tufo('peer:syn', iden=self.iden, mesh=self.mesh) )

    def runPlexSock(self, sock):
        '''
        Begin handling the given socket using the Plex().
        '''
        sock.on('link:sock:mesg', self._onLinkSockMesg )
        self.plex.addPlexSock(sock)
        self.fire('link:sock:init', sock=sock)

    def storm(self, evt, **evtinfo):
        '''
        Send an event to all the boxes in the mesh.
        '''
        mesg = (evt,evtinfo)

        self.dist(mesg)

        byts = msgenpack(mesg)

        sign = None
        if self.neur[1].get('neuron:usepki'):
            sign = self.pki.genByteSign(self.iden, byts)

        cert = self.pki.getTokenCert(self.iden)
        trees = self.getPathTrees()

        for tree in trees:
            self.relay(tree[0], tufo('neu:storm', tree=tree, byts=byts, sign=sign, iden=self.iden, cert=cert))

        return trees

    def relay(self, dest, mesg):
        '''
        Send a message to an adjacent neuron peer.
        '''
        sock = self.peers.get(dest)
        if sock == None:
            return False

        sock.tx(mesg)
        return True

    def route(self, iden, mesg, dsid=None):
        '''
        Route the given message to the dest neuron.

        Optionally specify dsid to deliver to a session
        connected to the remote neuron...
        '''
        ssid = None

        sess = s_session.current()
        if sess != None:
            ssid = sess.sid

        path = self.getLinkPath(self.iden, iden)
        if path == None:
            raise NoSuchPeer(iden)

        byts = msgenpack( mesg )

        nhop = path[1]
        data = tufo('neu:data', path=path, off=1, byts=byts, ssid=sess.sid, dsid=dsid)

        self.relay(nhop,data)

    def _onNeuLinkInit(self, event):
        iden0,iden1 = event[1].get('link')
        self.addPathLink(iden0,iden1)
        self.addPathLink(iden1,iden0)

        cert = event[1].get('cert')
        if cert != None:
            self.pki.loadCertToken(cert, save=True)

        mesh = event[1].get('mesh')
        if mesh != None:
            self._syncMeshDict(mesh)

    def _onNeuLinkFini(self, event):
        iden0,iden1 = event[1].get('link')
        self.delPathLink(iden0,iden1)
        self.delPathLink(iden1,iden0)

    def _onNeuStormMesg(self, sock, mesg):

        # This message is only valid from peer socks
        if not sock.get('peer:peer'):
            return

        # if they embedded a cert, check/load it
        cert = mesg[1].get('cert')
        if cert != None:
            print("STORM CERT: %r" % (self.pki.loadCertToken(cert),))

        tree = mesg[1].get('tree')
        byts = mesg[1].get('byts')
        sign = mesg[1].get('sign')
        iden = mesg[1].get('iden')

        if self.neur[1].get('neuron:usepki'):
            if not self.pki.isValidSign(iden, sign, byts):
                print('NEWP2 %s %r' % (iden,sign))
                print('NEWP2 TOKN %r' % (self.pki.getTokenTufo(iden),))
                print('NEWP2 MESG: %r' % (msgunpack(byts),) )
                return
            
        self.dist( msgunpack(byts) )

        for newt in tree[1]:
            self.relay(newt[0], tufo('neu:storm', tree=newt, byts=byts, iden=iden, sign=sign))


import json
import time
import logging
import msgpack
import traceback
import collections

#import Crypto.Hash.SHA256 as SHA256
#import Crypto.PublicKey.RSA as RSA
#import Crypto.Signature.PKCS1_v1_5 as PKCS15

import synapse.link as s_link
import synapse.async as s_async
import synapse.daemon as s_daemon
import synapse.dyndeps as s_dyndeps
import synapse.session as s_session
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.sched as s_sched
import synapse.lib.cache as s_cache

from synapse.common import *
from synapse.lib.threads import firethread

import synapse.impulse as s_impulse
from synapse.eventbus import EventBus

logger = logging.getLogger(__name__)

def openlink(link):
    '''
    Open a Dendrite() to a neuron mesh by link tufo.
    '''
    relay = s_link.getLinkRelay(link)
    return Dendrite(relay)

def openurl(url, **opts):
    '''
    Open a Dendrite() to a neuron mesh by url.
    '''
    link = s_link.chopLinkUrl(url)
    link[1].update(opts)
    return openlink(link)

class NeuSock(EventBus):

    def __init__(self, neur, dest, dsid):
        EventBus.__init__(self)
        self.dsid = dsid
        self.neur = neur
        self.dest = dest

    def tx(self, mesg):
        self.neur.route( self.dest, mesg, dsid=self.dsid)

class Neuron(s_daemon.Daemon):

    '''
    Neurons implement a peer-to-peer network mesh using any
    available synapse link protocol.  A neuron mesh provides service
    discovery and RMI transport to allow clients to reach services
    and APIs via the mesh itself.
    '''

    def __init__(self, core=None, pool=None):

        s_daemon.Daemon.__init__(self, core=core, pool=pool)

        self.sched = s_sched.Sched()

        self.model = self.core.getDataModel()
        if self.model == None:
            self.model = s_datamodel.DataModel()
            self.core.setDataModel(self.model)

        self.model.addTufoForm('neuron')
        self.model.addTufoProp('neuron','name')
        self.model.addTufoProp('neuron','super',ptype='int',defval=0)

        self.neur = self.core.formTufoByProp('neuron','self')
        self.iden = self.neur[0]

        self.mesh = {}
        self.peers = {}

        self.mesh['links'] = {}
        self.mesh['peers'] = { self.iden:self.neur }

        self.sockbyfrom = s_cache.Cache(maxtime=120)
        self.sockbyfrom.setOnMiss( self._getFakeSock )

        self.links = collections.defaultdict(set)

        self.linkpaths = s_cache.Cache(maxtime=30)
        self.linkpaths.setOnMiss( self._getLinkPath )

        self.setMesgFunc('neu:syn', self._onNeuSynMesg )
        self.setMesgFunc('neu:synack', self._onNeuSynAckMesg )

        self.setMesgFunc('neu:data', self._onNeuDataMesg )
        self.setMesgFunc('neu:storm', self._onNeuStormMesg )

        self.on('neu:link:up', self._onNeuLinkUp)
        self.on('neu:link:down', self._onNeuLinkDown)

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

    def addNeuShare(self, name, task, tags=()):
        '''
        Add a shared object to the neuron

        Example:

            task = ('synapse.cortex.openurl', ('ram:///',), {})

            neu.addNeuShare('hehe', task, tags=('foo.bar.baz',))

        '''
        item = s_dyndeps.runDynTask(task)
        self.share(name,item,tags=tags)

        jsinfo = dict(name=name, task=task, tags=tags)
        self.core.addTufoList(self.neur,'shared', json.dumps(jsinfo) )

    def addNeuListen(self, url):
        '''
        Add a link listen url to the neuron

        Example:

            neu.addNeuListen('tcp://0.0.0.0:9999')

        '''
        if self.hasopt.get(('listen',url)):
            raise DupOpt('listen: %s' % url)

        self.listen(url)
        self.core.addTufoList(self.neur,'listen',url)

    def addNeuConnect(self, url):
        '''
        Add a link connect url to the neuron

        Example:

            neu.addNeuConnect('tcp://mesh.kenshoto.com:9999')

        '''
        if self.hasopt.get(('connect',url)):
            raise DupOpt('connect: %s' % url)

        self.connect(url)
        self.core.addTufoList(self.neur,'connect',url)

    def _getFakeSock(self, idensid):
        iden,sid = idensid
        return NeuSock(self,iden,sid)

    def _onNeuSynMesg(self, sock, mesg):
        '''
        Handle a neu:syn hello from a newly connected peer.
        '''
        iden = mesg[1].get('iden')
        mesh = mesg[1].get('mesh')

        self._syncMeshDict(mesh)

        self._setPeerSock(iden,sock)

        sock.tx( tufo('neu:synack', iden=self.iden, mesh=self.mesh) )

    def _onNeuSynAckMesg(self, sock, mesg):
        '''
        Handle a neu:synack hello from a peer we connected to.
        '''
        iden = mesg[1].get('iden')
        mesh = mesg[1].get('mesh')

        self._syncMeshDict(mesh)
        self._setPeerSock(iden,sock)

    def _syncMeshDict(self, mesh):
        '''
        Ingest the mesh dict from a peer
        '''
        for iden,peer in mesh.get('peers',{}).items():
            if self.mesh['peers'].get(iden) == None:
                self.mesh['peers'][iden] = peer
                continue

        for (iden1,iden2),info in mesh.get('links',{}).items():
            self.addPathLink(iden1,iden2,**info)

    def _setPeerSock(self, iden, sock):
        '''
        Record that a peer is on the other end of sock.
        '''
        self.peers[iden] = sock

        def onfini():
            # FIXME peer lock and check if it's our sock?
            self.peers.pop(iden,None)
            self.storm('neu:link:down', link=(self.iden,iden))

        sock.onfini(onfini)
        self.storm('neu:link:up', link=(self.iden,iden))

    def _onNeuDataMesg(self, sock, mesg):
        '''
        Handle neu:data message ( most likely routing )
        '''
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

        dsid = mesg[1].get('dsid')
        if dsid != None:
            sess = self.cura.getSessBySid(dsid)
            if sess != None:
                sess.relay(newm)
            return

        ssid = mesg[1].get('ssid')
        sock = self.sockbyfrom.get( (path[0],ssid) )

        self._runLinkSockMesg( tufo('link:sock:mesg', sock=sock, mesg=newm) )

    def getPeerTufo(self):
        '''
        Return the "peer tufo" for this neuron.

        Example:

            peer = neu.getPeerTufo()

        '''
        return self.neur

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
        return self.model.getModelDict()

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
        #trees = []

        #done = self.links[self.iden]
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

        sock.tx( tufo('neu:syn', iden=self.iden, mesh=self.mesh) )

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
        trees = self.getPathTrees()

        for tree in trees:
            self.relay(tree[0], tufo('neu:storm', tree=tree, byts=byts))

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

    def _onNeuLinkUp(self, event):
        iden0,iden1 = event[1].get('link')
        self.addPathLink(iden0,iden1)
        self.addPathLink(iden1,iden0)

    def _onNeuLinkDown(self, event):
        iden0,iden1 = event[1].get('link')
        self.delPathLink(iden0,iden1)
        self.delPathLink(iden1,iden0)

    def _onNeuStormMesg(self, sock, mesg):
        tree = mesg[1].get('tree')

        byts = mesg[1].get('byts')
        self.dist( msgunpack(byts) )

        for newt in tree[1]:
            self.relay(newt[0], tufo('neu:storm', tree=newt, byts=byts))

class Dendrite(s_telepath.Proxy):

    def __init__(self, relay):

        s_telepath.Proxy.__init__(self, relay)

        self.sidbydest = {}

        self.onfini( self._onDendFini )

        self.itembytags = s_cache.Cache(maxtime=30)
        self.itembytags.setOnMiss( self._getByTag )

    def open(self, path):
        '''
        Open a connection to the named object on a neuron.

        Name should be in the form:
        * <iden>/<name>         - object "name" on neuron "iden"

        Example:

            # open object "name" on neuron "iden"
            prox = dend.open('%s/%s' % (iden,name))

        '''
        iden,name = path.split('/')
        job = self._tele_boss.initJob()
        mesg = tufo('tele:syn', sid=None, jid=job[0])

        self.route(iden,mesg)

        sid = self.sync(job)
        self.sidbydest[ (iden,name) ] = sid
        return Proxy( self, iden, name)

    def call(self, iden, name, task, ondone=None):
        '''
        Fire a  job to call the given task on a neuron shared object.
        '''
        sid = self.sidbydest.get( (iden,name) )
        job = self._tele_boss.initJob(ondone=ondone)
        mesg = tufo('tele:call', sid=sid, jid=job[0], name=name, task=task)
        self.route(iden,mesg)
        return job

    def _onDendFini(self):
        '''
        Make a best-effort attempt to tear down our sessions.
        '''

class Method:

    def __init__(self, prox, meth):
        self.meth = meth
        self.prox = prox

        self.name = prox.name
        self.iden = prox.iden
        self.dend = prox.dend

    def __call__(self, *args, **kwargs):
        ondone = kwargs.pop('ondone',None)
        task = ( self.meth, args, kwargs )
        job = self.dend.call(self.iden, self.name, task, ondone=ondone)
        if ondone != None:
            return job
        return self.dend.sync(job)

class Proxy:

    def __init__(self, dend, iden, name):
        self.iden = iden
        self.name = name
        self.dend = dend

    def __getattr__(self, name):
        meth = Method(self, name)
        setattr(self,name,meth)
        return meth

    def call(self, name, *args, **kwargs):
        ondone = kwargs.pop('ondone',None)
        task = (name,args,kwargs)
        return self.dend.call( self.iden, self.name, task, ondone=ondone)

    def sync(self, job, timeout=None):
        return self.dend.sync(job,timeout=timeout)



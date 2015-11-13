import time
import logging
import msgpack
import traceback
import collections

import Crypto.Hash.SHA256 as SHA256
import Crypto.PublicKey.RSA as RSA
import Crypto.Signature.PKCS1_v1_5 as PKCS15

import synapse.async as s_async
import synapse.cache as s_cache
import synapse.sched as s_sched
import synapse.cortex as s_cortex
import synapse.socket as s_socket
import synapse.daemon as s_daemon
import synapse.dyndeps as s_dyndeps
import synapse.reactor as s_reactor
import synapse.session as s_session
import synapse.threads as s_threads
import synapse.eventbus as s_eventbus

from synapse.common import *
from synapse.threads import firethread

import synapse.impulse as s_impulse
from synapse.eventbus import EventBus

logger = logging.getLogger(__name__)

class Neuron(s_impulse.PulseRelay):

    def __init__(self, core=None):
        s_impulse.PulseRelay.__init__(self)

        # note: neuron cortex should be "dedicated" to this neuron
        if core == None:
            core = s_cortex.openurl('ram:///')

        self.core = core
        self.rtor = s_reactor.Reactor()

        self.neur = core.formTufoByProp('neuron', 'self')

        self.iden = self.neur[0]
        self.dest = (self.iden,None)
        self.size = self.neur[1].get('neuron:size',4)

        self.pool = s_threads.Pool(size=self.size, maxsize=-1)
        self.onfini( self.pool.fini )

        self.peers = {}
        self.shares = {}

        self.cura = s_session.Curator(core)
        self.links = collections.defaultdict(set)

        self.linkpaths = s_cache.Cache(maxtime=30)
        self.linkpaths.setOnMiss( self._getLinkPath )

        # "router" layer events
        self.on('neu:data', self._onNeuData)
        self.on('neu:storm', self._onNeuStorm)

        # mesg handlers
        self.rtor.act('neu:syn', self._actNeuSyn)
        self.rtor.act('neu:call', self._actNeuCall)
        self.rtor.act('neu:ping', self._actNeuPing)

        #self.on('neu:sess:init', self._onNeuSessInit)

        self.on('neu:link:up', self._onNeuLinkUp)
        self.on('neu:link:down', self._onNeuLinkDown)

        #self.onfini( self._onNeuFini )

    def setNeuProp(self, prop, valu):
        '''
        Set a persistant property for this neuron.

        Example:

            neu.setNeuProp('foo',10)

        '''
        self.core.setTufoProp(tufo,prop,valu)

    def getNeuProp(self, prop):
        '''
        Retrieve a persistant neuron property.

        Example:

            foo = neu.getNeuProp('foo')

        '''
        return self.neur[1].get(prop)

    def share(self, name, item):
        '''
        Share an object to the neuron mesh.
        '''
        self.shares[name] = item

    def getPathTrees(self):
        '''
        Return a list of trees for shortest path broadcast.
        '''
        done = set()
        trees = []

        done = self.links[self.iden]
        trees = [ (i,[]) for i in self.links[self.iden] ]

        todo = list(trees)
        while todo:
            node = todo.pop()
            for iden in self.links[ node[0] ]:
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

    def addPathLink(self, iden1, iden2):
        '''
        Add a link to the known paths cache.
        '''
        self.links[iden1].add(iden2)

    def addPathLinks(self, links):
        '''
        Add multiple (id1,id2) link tuples.
        '''
        [ self.addPathLink(iden1,iden2) for (iden1,iden2) in links ]

    def getLinkPath(self, iden1, iden2):
        '''
        Find the shortest path from iden1 to iden2
        '''
        #return self.linkpaths.get( (iden1,iden2) )
        return self._getLinkPath( (iden1,iden2) )

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

    def getIden(self):
        '''
        Return the guid/iden for the Neuron.

        Example:

            iden = neu.getIden()

        '''
        return self.iden

    def link(self, neu):
        '''
        Link ourself to another neuron.

        Example:

            neu1.link( neu2 )

        '''
        iden = neu.getIden()

        self.peers[iden] = neu

        self.addPathLink( self.iden, iden )
        self.addPathLink( iden, self.iden )

        mylinks = self.getPathLinks()
        hislinks = list( neu.getPathLinks() )

        # FIXME callback for link tear down!

        neu.addPathLinks(mylinks)
        self.addPathLinks(hislinks)

        # ensure both chans are active
        neu.openchan( self.iden )
        self.openchan( iden )

        self._runLinkRecv(neu)
        self._runLinkSend(neu)

        links = mylinks + hislinks
        self.storm('neu:link:up', link=(self.iden,iden))

    def storm(self, evt, **evtinfo):
        '''
        Send an event to all the boxes in the mesh.
        '''
        byts = msgenpack( (evt,evtinfo) )
        for tree in self.getPathTrees():
            self.relay(tree[0], tufo('neu:storm', tree=tree, byts=byts))

    @firethread
    def _runLinkRecv(self, neu):
        with neu:
            while not self.isfini:
                evts = neu.poll(self.iden, timeout=4)
                if evts:
                    self.distall(evts)

    @firethread
    def _runLinkSend(self, neu):
        iden = neu.getIden()
        with neu:
            while not self.isfini:
                evts = self.poll(iden, timeout=1)
                if evts:
                    neu.distall(evts)

    def reply(self, mesg, evt, **evtinfo):
        '''
        Send a response to a channel consumer on a given neuron.
        '''
        dest = mesg[1].get('from')

        evtinfo['jid'] = mesg[1].get('jid')
        mesg = (evt,evtinfo)
        self.route( dest, mesg)

    def route(self, dest, mesg):
        '''
        Route the given message to the dest neuron.
        '''
        iden,chan = dest
        path = self.getLinkPath(self.iden, iden)
        if path == None:
            raise NoSuchPeer(iden)

        byts = msgenpack( mesg )

        nhop = path[1]
        data = tufo('neu:data', path=path, off=1, byts=byts, chan=chan)

        self.relay(nhop,data)

    def _onNeuLinkUp(self, event):
        iden0,iden1 = event[1].get('link')
        self.addPathLink(iden0,iden1)
        self.addPathLink(iden1,iden0)

    def _onNeuLinkDown(self, event):
        iden0,iden1 = event[1].get('link')
        self.delPathLink(iden0,iden1)
        self.delPathLink(iden1,iden0)

    def _actNeuSyn(self, event):
        sess = self.cura.getNewSess()
        return sess.sid

    def _actNeuPing(self, event):
        return {'shared':list(self.shares.keys())}

    def _onNeuData(self, event):
        off = event[1].get('off') + 1
        path = event[1].get('path')

        # are we the final hop?
        if len(path) == off:
            chan = event[1].get('chan')
            byts = event[1].get('byts')
            mesg = msgunpack(byts)

            # is it for one of our chans?
            if chan != None:
                self.relay(chan,mesg)
                return

            # our workers handle our messages
            self.pool.call( self._runDataMesg, mesg )
            return

        # route it along...
        dest = path[off]
        event[1]['off'] = off
        self.relay(dest, event)
        # FIXME if the next hop is dead we could re-route

    def _runDataMesg(self, mesg):
        try:
            ret = self.rtor.react(mesg)
            self.reply(mesg, ret=ret)

        except Exception as e:
            self.reply(mesg, **excinfo(e))

    def reply(self, mesg, **evtinfo):
        jid = mesg[1].get('jid')
        dest = mesg[1].get('from')
        mesg = tufo('job:done', jid=jid, **evtinfo)
        self.route(dest,mesg)

    def _onNeuStorm(self, event):
        tree = event[1].get('tree')
        for newt in tree[1]:
            self.relay(newt[0], event)

        byts = event[1].get('byts')
        event = msgunpack(byts)
        self.dist(event)

    def _actNeuCall(self, event):

        name,api,args,kwargs = event[1].get('neutask')

        item = self.shares.get(name)
        if item == None:
            raise NoSuchObj(name)

        meth = getattr(item,api,None)
        if meth == None:
            raise NoSuchMeth(api)

        sid = event[1].get('sid')
        if sid == None:
            raise SidNotFound()

        sess = self.cura.getSessBySid(sid)
        if sess == None:
            raise NoSuchSess(sid)

        with sess:
            return meth(*args,**kwargs)

    # fake these for local use
    def __enter__(self):
        return self

    def __exit__(self, exc, cls, tb):
        return

class Meth:

    def __init__(self, proxy, api):
        self.api = api
        self.proxy = proxy
        self.dend = proxy.dend
        self.iden = proxy.iden
        self.name = proxy.name

    def __call__(self, *args, **kwargs):
        return self.dend.call( self.iden, self.name, self.api, *args, **kwargs)

class Proxy:

    def __init__(self, dend, iden, name):
        self.iden = iden
        self.name = name
        self.dend = dend

    def __getattr__(self, name):
        meth = Meth(self, name)
        setattr(self,name,meth)
        return meth

class Dendrite(EventBus):
    '''
    A Dendrite is a "Leaf" in the Neuron mesh.
    '''

    def __init__(self, neu, size=3):
        EventBus.__init__(self)

        self.boss = s_async.Boss()
        self.pool = s_threads.Pool(size=size)

        self.boss.setBossPool(self.pool)

        self.on('job:done', self.boss.dist)

        self.onfini( self.pool.fini )
        self.onfini( self.boss.fini )

        self.neu = neu
        self.chan = guidstr()       # our chan on neu
        self.iden = neu.getIden()   # our neuron's iden

        self.dest = (self.iden,self.chan)

        self.sidbydest = {}        # (iden,chan):sid

        self._recv_thr = self._runRecvThread()

    def getSidByDest(self, dest):
        '''
        Return a session id for the given neuron.

        Example:

            dest = (iden,chan)
            sid = cli.getSidByDest(dest)

        '''
        sid = self.sidbydest.get(dest)
        if sid == None:
            # bypass trans() to avoid infinite loop
            sid = self._fire_trans(dest,tufo('neu:syn'))
            self.sidbydest[dest] = sid
        return sid

    @firethread
    def _runRecvThread(self):
        while not self.isfini:
            try:

                # get our own socket
                with self.neu as neu:
                    evts = neu.poll(self.chan, timeout=2)
                    if evts:
                        self.distall(evts)

            except Exception as e:
                traceback.print_exc()

    def find(self, tag):
        '''
        Find objects with the given tag.
        '''

    #def search(self, tag):

    def open(self, dest, name, authinfo=None):
        '''
        Open a Neuron proxy for the given object name.

        Example:

            foo = cli.open(dest,'foo')
            foo.dostuff(10)

        Notes:

            The proxy class allows async calling by adding
            onfini kwarg to the API call.

        '''
        # get a session to the neuron
        self.getSidByDest(dest)
        return Proxy(self, dest, name)

    def call(self, iden, name, api, *args, **kwargs):
        '''
        Call an API shared within a remote Neuron.

        Example:

            ret = cli.call(iden, name, 'getFooByBar', bar)

        Notes:

            Syntax sugar is provided by the Proxy via open().

        '''
        onfini = kwargs.pop('onfini',None)
        neutask = (name,api,args,kwargs)
        mesg = tufo('neu:call', neutask=neutask)
        dest = (iden,None)
        return self.trans(dest,mesg,onfini=onfini)

    def ping(self, dest):
        '''
        Ping the target neuron and return his basic info.

        Example:

            info = cli.ping(dest)

        '''
        return self.trans(dest,tufo('neu:ping'))

    def trans(self, dest, mesg, onfini=None):
        '''
        Perform a "transaction" with the given neuron.
        '''
        mesg[1]['sid'] = self.getSidByDest(dest)
        return self._fire_trans(dest, mesg, onfini=onfini)

    #def route(self, dest, chan, evt, **evtinfo):
        #'''
        #Route a message to the given iden/chan in the mesh.
        #'''
        #return self.neu.route(dest,chan,evt,**evtinfo)

    #def reply(self, mesg, evt, **evtinfo):
        #'''
        #'''
        #dest = mesg[1].get('from')
        #evtinfo['jid'] = mesg[1].get('jid')
        #newm = (evt,**evtinfo)
        #self._fire_mesg(dest,
        #self.route(dest,chan,'job:done',**evtinfo)

    def _fire_trans(self, dest, mesg, onfini=None):

        jid = guidstr()
        mesg[1]['jid'] = jid
        job = self.boss.initJob(jid,onfini=onfini)

        self._fire_mesg(dest,mesg)
        self.boss.waitJob(jid)

        return s_async.jobret(job)

    def _fire_mesg(self, dest, mesg):
        '''
        Fire a message to a given neuron by iden.

        Notes:
            * this API adds our "chan" so responses may return

        '''
        mesg[1]['from'] = self.dest
        self.neu.route(dest, mesg)

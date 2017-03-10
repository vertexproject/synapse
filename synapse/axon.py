import os
import json
import hashlib
import logging
import tempfile
import threading
import multiprocessing

import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.heap as s_heap
import synapse.lib.persist as s_persist
import synapse.lib.service as s_service
import synapse.lib.thishost as s_thishost
import synapse.lib.thisplat as s_thisplat

from synapse.common import *

logger = logging.getLogger(__name__)

megabyte = 1024000
gigabyte = 1024000000

chunksize = megabyte * 10

class HashSet:

    def __init__(self):

        self.size = 0

        # BEWARE ORDER MATTERS FOR guid()
        self.hashes = [
            ('md5',hashlib.md5()),
            ('sha1',hashlib.sha1()),
            ('sha256',hashlib.sha256()),
            ('sha512',hashlib.sha512())
        ]

    def guid(self):
        '''
        Use elements from this hash set to create a unique
        (re)identifier.
        '''
        iden = hashlib.md5()
        props = {'size':self.size}

        for name,item in self.hashes:
            iden.update(item.digest())
            props[name] = item.hexdigest()

        return iden.hexdigest(),props

    def eatfd(self, fd):
        '''
        Consume all the bytes from a file like object.

        Example:

            hset = HashSet()
            hset.eatfd(fd)

        '''
        fd.seek(0)
        byts = fd.read(10000000)
        while byts:
            self.update(byts)
            byts = fd.read(10000000)

        return self.guid()

    def update(self, byts):
        '''
        Update all the hashes in the set with the given bytes.
        '''
        self.size += len(byts)
        [ h[1].update(byts) for h in self.hashes ]

    def digests(self):
        '''
        Return a list of (name,digest) tuples for the hashes in the set.
        '''
        return [ (name,item.hexdigest()) for (name,item) in self.hashes ]

threedays = ((60 * 60) * 24) * 3

megabyte = 1024000
gigabyte = 1024000000
terabyte = 1024000000000

axontag = 'class.synapse.axon.Axon'

class AxonHost(s_eventbus.EventBus):
    '''
    Manage multiple axons on a given host.
    '''
    def __init__(self, datadir, **opts):
        s_eventbus.EventBus.__init__(self)

        self.datadir = gendir(datadir)

        self.opts = opts
        self.lock = threading.Lock()

        self.axons = {}
        self.axonbus = None
        self.axonforks = {}

        self.onfini( self._onAxonHostFini )

        self.opts.setdefault('autorun',0)               # how many axons to auto-start
        self.opts.setdefault('axonbus','')              # url to axonbus

        self.opts.setdefault('bytemax',terabyte)        # by default make each Axon 1 Terabyte
        self.opts.setdefault('syncmax',gigabyte * 10)   # 

        self.opts.setdefault('hostname', s_thishost.get('hostname') ) # allow override for testing

        url = self.opts.get('axonbus')
        if url:
            self.axonbus = s_service.openurl(url)
            self.axonbus.runSynSvc(guid(),self)

        for name in os.listdir(self.datadir):

            if not name.endswith('.axon'):
                continue

            iden,_ = name.split('.',1)

            self._fireAxonIden(iden)

        # fire auto-run axons
        auto = self.opts.get('autorun')
        while len(self.axons) < auto:
            self.add()

    def _fireAxonIden(self, iden):
        axondir = gendir(self.datadir,'%s.axon' % iden)

        opts = dict(self.opts)
        jsopts = jsload(axondir,'axon.opts')
        if jsopts != None:
            opts.update( jsopts )

        self.axons[iden] = Axon(axondir,**opts)

    def _onAxonHostFini(self):
        for axon in list(self.axons.values()):
            axon.fini()

    def info(self):
        '''
        Return info for attempting to allocate clones and check health.
        '''
        usage = self.usage()
        return {
            'count':len(self.axons),
            'free':usage.get('free',0),
            'used':usage.get('used',0),
            'hostname':self.opts.get('hostname'),
        }

    def add(self, **opts):
        '''
        Add a new axon to the AxonHost.

        Example:

            # add another axon to the host with defaults
            axfo = axho.add()

        '''
        iden = guid()
        opts['iden'] = iden     # store iden as a specified option

        fullopts = dict(self.opts)
        fullopts.update(opts)

        bytemax = fullopts.get('bytemax')
        if not fullopts.get('clone'):
            bytemax += fullopts.get('syncmax')

        volinfo = s_thisplat.getVolInfo(self.datadir)

        free = volinfo.get('free')
        total = volinfo.get('total')

        if bytemax > free:
            raise NotEnoughFree(bytemax)

        axondir = gendir(self.datadir,'%s.axon' % iden)

        jssave(opts,axondir,'axon.opts')

        # FIXME fork
        axon = Axon(axondir,**fullopts)

        self.axons[iden] = axon

        return axon.axfo

    def usage(self):
        '''
        Return volume usage info.
        '''
        volinfo = s_thisplat.getVolInfo( self.datadir )
        return volinfo

axontag = 'class.synapse.axon.Axon'

class AxonMixin:
    '''
    The parts of the Axon which must be executed locally in proxy cases.
    ( used as mixin for both Axon and AxonProxy )
    '''
    def eatfd(self, fd):

        hset = HashSet()
        iden,props = hset.eatfd(fd)

        blob = self.byiden(iden)
        if blob != None:
            return blob

        fd.seek(0)

        sess = self.alloc( props.get('size') )

        byts = fd.read(10000000)
        while byts:
            retn = self.chunk(sess,byts)
            byts = fd.read(10000000)

        return retn

    def eatbytes(self, byts):
        hset = HashSet()

        hset.update(byts)
        iden,props = hset.guid()
        blob = self.byiden(iden)
        if blob != None:
            return blob

        sess = self.alloc( props.get('size') )

        for chnk in chunks(byts,10000000):
            blob = self.chunk(sess,chnk)

        return blob

class AxonCluster(AxonMixin):
    '''
    Present a singular axon API from an axon cluster.
    '''
    def __init__(self, svcprox):
        self.axons = {}
        self.saves = {}

        self.svcprox = svcprox

    def has(self, htype, hvalu, bytag=axontag):
        '''
        Returns True if any of the axons in the cluster contain the given hash.

        Example:

            if not axapi.has('sha256',filehash):
                dostuff()

        '''
        dyntask = gentask('has',htype,hvalu)
        for svcfo,retval in self.svcprox.callByTag(bytag,dyntask):
            if retval:
                return True

        return False

    def _getSvcAxon(self, iden):

        svcfo = self.svcprox.getSynSvc(iden)
        if svcfo == None:
            return None

        axon = self.axons.get(iden)
        if axon == None:

            link = svcfo[1].get('link')
            if link == None:
                return None

            def onfini():
                self.axons.pop(iden,None)

            try:

                # copy before we frob it
                #link = (link[0],dict(link[1]))
                #link[1]['once'] = True

                axon = s_telepath.openlink(link)
                self.axons[iden] = axon

                axon.onfini( onfini )

            except Exception as e:
                return None

        return axon

    def find(self, htype, hvalu, bytag=axontag):
        '''
        Find and return any blobs with the given hash.

        Example:

            blobs = axon.find('sha256',valu)

        '''
        retblobs = []
        dyntask = gentask('find',htype,hvalu)
        for svcfo,blobs in self.svcprox.callByTag(bytag,dyntask):

            if not blobs:
                continue

            try:

                axon = self._getSvcAxon(svcfo[0])
                if axon == None:
                    continue

                [ b[1].__setitem__('.axon',svcfo[0]) for b in blobs ]
                retblobs.extend(blobs)

            except Exception as e:
                logger.warning('AxonApi find: %s %s' % (svcfo[0],e))

        return retblobs

    def iterblob(self, blob):
        # try to use the blob they wanted, otherwise look it up again and iter.
        axon = None

        iden = blob[1].get('.axon')
        axon = self._getSvcAxon(iden)

        if axon == None:
            valu = blob[1].get('axon:blob:sha256')
            for byts in self.bytes('sha256',valu):
                yield byts
            return

        for byts in axon.iterblob(blob):
            yield byts

    def bytes(self, htype, hvalu, bytag=axontag):

        dyntask = gentask('find',htype,hvalu)
        for svcfo,blobs in self.svcprox.callByTag(bytag,dyntask):

            if not blobs:
                continue

            axon = self._getSvcAxon(svcfo[0])
            if axon == None:
                continue

            for byts in axon.bytes(htype,hvalu):
                yield byts

            return

    def wants(self, htype, hvalu, size, bytag=axontag):
        if self.has(htype,hvalu,bytag=bytag):
            return None
        return self.alloc(size,bytag=bytag)

    def alloc(self, size, bytag=axontag):
        '''
        Allocate a new block within an axon to save size bytes.

        Returns an iden to use for subsequent calls to axon.chunk()

        '''
        axons = self._getWrAxons(bytag=bytag)
        if not len(axons):
            raise NoWritableAxons(bytag)

        # FIXME shuffle/randomize

        for axon in axons:
            iden = axon.alloc(size)
            self.saves[iden] = { 'iden':iden, 'axon':axon }
            return iden

    def chunk(self, iden, byts):
        info = self.saves.get(iden)
        if info == None:
            NoSuchIden(iden)

        axon = info.get('axon')
        retn = axon.chunk(iden,byts)
        if retn != None:
            self.saves.pop(iden,None)

        return retn

    def _getWrAxons(self, bytag=axontag):

        wraxons = []

        # FIXME cache this call for a few seconds
        dyntask = gentask('getAxonInfo')
        for svcfo,axfo in self.svcprox.callByTag(bytag,dyntask):

            if axfo[1]['opts'].get('ro'):
                continue

            axon = self._getSvcAxon(svcfo[0])
            if axon == None:
                continue

            wraxons.append(axon)

        return wraxons

class Axon(s_eventbus.EventBus,AxonMixin):
    '''
    An Axon acts as a binary blob store with hash based indexing/retrieval.

    Opts:

        clone = <iden>          # set if we are a clone (of iden)
        clones = <count>        # how many clones should we try to create?
        syncsize = <size>       # approx max size for each sync file
        synckeep = <seconds>    # how long to keep an axon sync block

    '''
    def __init__(self, axondir, **opts):
        s_eventbus.EventBus.__init__(self)

        self.inprog = {}
        self.axondir = gendir(axondir)
        self.clonedir = gendir(axondir,'clones')

        self.clones = {}
        self.cloneinfo = {}
        self.clonehosts = set()
        self.clonelock = threading.Lock()

        self.readyclones = set()                # iden of each clone added as it comes up
        self.clonesready = threading.Event()    # set once all clones are up and running

        self.opts = opts
        self.axonbus = None

        self.iden = self.opts.get('iden')
        self.tags = self.opts.get('tags',())

        self.opts.setdefault('ro',False)
        self.opts.setdefault('clone','')   # are we a clone?
        self.opts.setdefault('clones',2)   # how many clones do we want?
        self.opts.setdefault('axonbus','')  # do we have an axon svcbus?

        self.opts.setdefault('hostname', s_thishost.get('hostname') )

        self.opts.setdefault('listen','tcp://0.0.0.0:0/axon') # our default "ephemeral" listener

        # if we're a clone, we're read-only and have no clones
        if self.opts.get('clone'):
            self.opts['ro'] = True
            self.opts['clones'] = 0

        self.opts.setdefault('synckeep',threedays)
        self.opts.setdefault('syncsize',gigabyte*10)

        corepath = os.path.join(self.axondir,'axon.db')
        self.core = s_cortex.openurl('sqlite:///%s' % corepath)

        fd = genfile(axondir,'axon.heap')

        self.link = None
        self.heap = s_heap.Heap(fd)
        self.dmon = s_daemon.Daemon()

        lisn = self.opts.get('listen')
        if lisn:
            self.link = self.dmon.listen(lisn)

        self.axfo = (self.iden,{})

        self.axthrs = set()

        self.setAxonInfo('link',self.link)
        self.setAxonInfo('opts',self.opts)

        self.dmon.share('axon',self)

        # create a reactor to unwrap core/heap sync events
        self.syncact = s_reactor.Reactor()
        self.syncact.act('heap:sync', self.heap.sync )
        self.syncact.act('core:sync', self.core.sync )

        # wrap core/heap sync events as axon:sync events
        self.core.on('core:sync', self._fireAxonSync )
        self.heap.on('heap:sync', self._fireAxonSync )

        # model details for the actual byte blobs
        self.core.addTufoForm('axon:blob',ptype='guid')
        self.core.addTufoProp('axon:blob','off', ptype='int',req=True)
        self.core.addTufoProp('axon:blob','size', ptype='int',req=True)

        self.core.addTufoProp('axon:blob','md5', ptype='hash:md5',req=True)
        self.core.addTufoProp('axon:blob','sha1', ptype='hash:sha1',req=True)
        self.core.addTufoProp('axon:blob','sha256', ptype='hash:sha256',req=True)
        self.core.addTufoProp('axon:blob','sha512', ptype='hash:sha512',req=True)

        self.core.addTufoForm('axon:clone',ptype='guid')

        dirname = gendir(axondir,'sync')
        syncopts = self.opts.get('syncopts',{})

        self.syncdir = None

        self.onfini( self._onAxonFini )

        self.onfini( self.core.fini )
        self.onfini( self.heap.fini )
        self.onfini( self.dmon.fini )

        # if we're not a clone, create a sync dir
        if not self.opts.get('clone'):
            self.syncdir = s_persist.Dir(dirname,**syncopts)
            self.onfini( self.syncdir.fini )

            self.on('axon:sync', self.syncdir.add )

        self.axcthr = None

        # share last to avoid startup races
        busurl = self.opts.get('axonbus')
        if busurl:
            self.axonbus = s_service.openurl(busurl)

            props = {'link':self.link,'tags':self.tags}
            self.axonbus.runSynSvc(self.iden,self,**props)

            self.axcthr = self._fireAxonClones()

    @firethread
    def _fireAxonClones(self):

        clones = self.core.getTufosByProp('axon:clone')
        for axfo in clones:
            iden = axfo[1].get('axon:clone')
            host = axfo[1].get('axon:clone:host')

            self.clonehosts.add(host)

            self._initAxonClone(iden)

        self._findAxonClones()

    def _waitClonesReady(self, timeout=None):
        '''
        Wait for the "clonesready" event which is set during
        initialization once running/online clone count is full.
        '''
        self.clonesready.wait(timeout=timeout)
        return self.clonesready.is_set()

    def _addCloneReady(self, iden):
        '''
        Add the clone iden to the ready list and potentially
        set the "clonesready" event.
        '''

        if iden in self.readyclones:
            return

        count = self.opts.get('clones')
        with self.clonelock:
            self.readyclones.add(iden)
            if len(self.readyclones) == count:
                self.clonesready.set()

    def _findAxonClones(self):
        '''
        Sleep/Loop attempting to find AxonHost instances to clone for us.
        '''
        while len(self.clones) < self.opts.get('clones'):

            if self.isfini:
                break

            try:

                axfo = self._findAxonClone()
                if axfo == None:
                    time.sleep(1)
                    continue

                self._initAxonClone(axfo[0])

            except Exception as e:
                logger.exception('findAxonClones')

    def _findAxonClone(self):
        myhost = self.opts.get('hostname')
        bytemax = self.opts.get('bytemax')

        dyntask = gentask('info')
        hostinfo = list(self.axonbus.callByTag('class.synapse.axon.AxonHost', dyntask))

        hostinfo = [ h for h in hostinfo if h[1].get('free') > bytemax ]
        hostinfo = [ h for h in hostinfo if h[1].get('hostname') != myhost ]

        def hostkey(x):
            used = x[1].get('used')
            count = x[1].get('count')
            return (count,used)

        for svcfo,ahinfo in sorted(hostinfo,key=hostkey):
            try:
                host = ahinfo.get('hostname')
                if host in self.clonehosts:
                    continue

                props = {'clone':self.iden,'bytemax':bytemax,'host':host}
                axfo = self.axonbus.callByIden(svcfo[0],'add',**props)

                tufo = self.core.formTufoByProp('axon:clone',axfo[0], host=host)
                self.clonehosts.add(host)

                return axfo

            except Exception as e:
                logger.exception('findAxonClone')

    def _initAxonClone(self, iden):
        tufo = self.core.formTufoByProp('axon:clone',iden)

        poff = self.syncdir.getIdenOffset(iden)
        self.cloneinfo[iden] = {'off':poff.get()}

        thr = self._fireAxonClone(iden,poff)
        self.axthrs.add(thr)

    @firethread
    def _fireAxonClone(self, iden, poff):

        # axon iden is persistent ( and used as svc name )
        clonefo = self.cloneinfo.get(iden)
        with poff:

            while not self.isfini:

                try:

                    svcfo = self.axonbus.getSynSvcByName(iden)

                    link = svcfo[1].get('link')
                    if link == None:
                        raise Exception('NoLinkFor: %s' % (iden,))

                    with s_telepath.openlink(link) as axon:

                        self._addCloneReady(iden)

                        self.clones[iden] = axon

                        #if oldp == None:
                            #self.cloned.release()

                        off = poff.get()

                        for noff,item in self.syncdir.items(off):
                            axon.sync(item)
                            poff.set(noff)

                            clonefo['off'] = noff

                except Exception as e:

                    logger.exception('_fireAxonClone')

                    if self.isfini:
                        break

                    time.sleep(1)

    def getAxonInfo(self):
        '''
        Return a dictionary of salient info about an axon.
        '''
        return self.axfo

    def setAxonInfo(self, prop, valu):
        self.axfo[1][prop] = valu

    def find(self, htype, hvalu):
        '''
        Returns a list of blob tufos for hashes in the axon.

        Example:

            blobs = axon.find('sha256',x)

        '''
        return self.core.getTufosByProp('axon:blob:%s' % htype, valu=hvalu)

    def bytes(self, htype, hvalu):
        '''
        Yield chunks of bytes for the given hash value.

        Example:

            for byts in axon.bytes('md5',md5sum):
                fd.write(byts)

        '''
        blob = self.core.getTufoByProp('axon:blob:%s' % htype, valu=hvalu)
        return self.iterblob(blob)

    def iterblob(self, blob):
        '''
        Yield byts blocks from the give blob until complete.

        Example:

            for byts in axon.iterAxonBlob(blob):
                dostuff(byts)

        '''
        off = blob[1].get('axon:blob:off')
        size = blob[1].get('axon:blob:size')

        for byts in self.heap.readiter(off,size):
            yield byts

    def wants(self, htype, hvalu, size):
        '''
        Single round trip call to has and possibly alloc.

        Example:

            iden = axon.wants('sha256',valu,size)
            if iden != None:
                for byts in chunks(filebytes,onemeg):
                    axon.chunk(iden,byts)

        '''
        if self.has(htype,hvalu):
            return None

        return self.alloc(size)

    def _fireAxonSync(self, mesg):
        self.fire('axon:sync', mesg=mesg)

    def sync(self, mesg):
        '''
        Consume an axon:sync event (only if we are a clone).
        '''
        if not self.opts.get('clone'):
            raise Exception('Not A Clone')

        self.syncact.react(mesg[1].get('mesg'))

    def syncs(self, msgs):
        '''
        Consume a list of axon:sync events.
        '''
        with self.core.getCoreXact():
            [ self.sync(m) for m in msgs ]

    def _onAxonFini(self):
        # join clone threads
        [ thr.join(timeout=2) for thr in list(self.axthrs) ]
        if self.axcthr != None:
            self.axcthr.join(timeout=2)

    def alloc(self, size):
        '''
        Initialize a new blob upload context within this axon.

        Example:

            iden = axon.alloc(len(byts))

            for b in chunks(byts,10240):
                axon.chunk(iden,b)

        '''
        if self.opts.get('clone'):
            raise Exception('Axon Is Clone') # FIXME

        iden = guid()
        off = self.heap.alloc(size)

        self.inprog[iden] = {'size':size,'off':off,'cur':off,'maxoff':off+size,'hashset':HashSet()}

        return iden

    def chunk(self, iden, byts):
        '''
        Save a chunk of a blob allocated with alloc().
        '''
        info = self.inprog.get(iden)

        if info == None:
            NoSuchIden(iden)

        cur = info.get('cur')
        self.heap.writeoff(cur,byts)

        info['cur'] += len(byts)

        hset =info.get('hashset')
        hset.update(byts)

        # if the upload is complete, fire the add event
        if info['cur'] == info['maxoff']:

            self.inprog.pop(iden,None)

            off = info.get('off')
            iden,props = hset.guid()

            return self.core.formTufoByProp('axon:blob', iden, off=off, **props)

    def has(self, htype, hvalu):
        '''
        Return True if the Axon contains the given hash type/valu combo.

        Example:

            if not axon.has('sha256', shaval):
                stuff()

        '''
        tufo = self.core.getTufoByProp('axon:blob:%s' % htype, hvalu)
        return tufo != None

    def byiden(self, iden):
        return self.core.getTufoByProp('axon:blob',iden)


class AxonProxy(s_telepath.Proxy,AxonMixin):
    pass

def openurl(url, **opts):
    '''
    Open a URL to a remote Axon
    '''
    return s_telepath.openclass(AxonProxy, url, **opts)

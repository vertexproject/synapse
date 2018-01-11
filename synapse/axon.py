import os
import stat
import time
import random
import logging
import threading

import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.dyndeps as s_dyndeps
import synapse.reactor as s_reactor
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.heap as s_heap
import synapse.lib.tufo as s_tufo
import synapse.lib.config as s_config
import synapse.lib.persist as s_persist
import synapse.lib.service as s_service
import synapse.lib.thishost as s_thishost
import synapse.lib.thisplat as s_thisplat

# for backward compat (HashSet moved from this module to synapse.lib.hashset )
from synapse.lib.hashset import *

logger = logging.getLogger(__name__)

megabyte = 1024000
gigabyte = 1024000000
terabyte = 1024000000000
chunksize = megabyte * 10
axontag = 'class.synapse.axon.Axon'

_fs_attrs = ('st_mode', 'st_nlink', 'st_size', 'st_atime', 'st_ctime', 'st_mtime')

class AxonHost(s_config.Config):
    '''
    Manage multiple axons on a given host.
    '''
    def __init__(self, datadir, **opts):
        s_config.Config.__init__(self)

        self.datadir = s_common.gendir(datadir)

        self.iden = s_common.guid()  # A non-persistent iden for identification
        self.lock = threading.Lock()

        self.axons = {}  # iden -> Axon mapping.
        self.axonbus = None
        self.axonforks = {}
        self.cloneaxons = []  # List of idens which are clones.

        self.onfini(self._onAxonHostFini)

        self.setConfOpts(opts)

        self._axonconfs = [_name for _name, _ in Axon._axon_confdefs()]

        # track the total number of bytes which may be used by axons for startup operations
        self.usedspace = 0

        for name in os.listdir(self.datadir):

            if not name.endswith('.axon'):
                continue

            iden, _ = name.split('.', 1)

            logger.debug('Bringing Axon [%s] online', iden)
            self._fireAxonIden(iden)

        # fire auto-run axons
        auto = self.getConfOpt('axonhost:autorun')
        while (len(self.axons) - len(self.cloneaxons)) < auto:
            self.add()

        url = self.getConfOpt('axon:axonbus')
        if url:
            self.axonbus = s_service.openurl(url)
            self.onfini(self.axonbus.fini)
            self.axonbus.runSynSvc(self.iden, self)

    @staticmethod
    @s_config.confdef(name='axonhost')
    def _axonhost_confdefs():
        confdefs = (
            ('axonhost:autorun', {'type': 'int', 'defval': 0,
                                  'doc': 'Number of Axons to autostart.'}),
            ('axon:axonbus', {'type': 'str', 'defval': '',
                                  'doc': 'URL to an axonbus'}),
            ('axon:bytemax', {'type': 'int', 'defval': terabyte,
                                  'doc': 'Max size of each axon created by the host.'}),
            ('axon:listen', {'type': 'str', 'defval': 'tcp://0.0.0.0:0/axon',
                             'doc': 'Default listener URLs for the axons created by this host', }),
            ('axon:tags', {'defval': (),
                           'doc': 'Tuple of tag values for the axon to add when sharing over a Axon servicebus.'}),
            ('axon:syncopts', {'defval': {},
                               'doc': 'kwarg Options used when making a persistent sync directory for axons.'}),
            ('axon:clones', {'type': 'int', 'defval': 2,
                                 'doc': 'The default number of clones for a axon.'}),
            ('axonhost:maxsize', {'type': 'int', 'defval': 0,
                                  'doc': 'Max total allocations for Axons created by the host. '
                                         'Only applies if set to a positive integer.'}),
            ('axon:hostname', {'type': 'str', 'defval': s_thishost.get('hostname'),
                                   'doc': 'AxonHost hostname'}),
        )
        return confdefs

    def _fireAxonIden(self, iden):
        '''
        This is used to bring existing Axons owned by the AxonHost online.
        '''
        axondir = s_common.gendir(self.datadir, '%s.axon' % iden)

        opts = self.makeAxonOpts()
        jsopts = s_common.jsload(axondir, 'axon.opts')
        if jsopts is not None:
            opts.update(jsopts)

        # Special case where the axonbus may update - we want to ensure
        # we're passing the latest axonbus to the Axon so it can register
        # itself properly.
        axonbus = opts.get('axon:axonbus')
        if axonbus is not None:
            myaxonbus = self.getConfOpt('axon:axonbus')
            if axonbus != myaxonbus:
                opts['axon:axonbus'] = myaxonbus
                s_common.jssave(opts, axondir, 'axon.opts')

        logger.debug('Bringing Axon online from [%s]', axondir)
        self.axons[iden] = Axon(axondir, **opts)

        bytemax = opts.get('axon:bytemax')
        clone = opts.get('axon:clone')

        if clone:
            self.cloneaxons.append(iden)
        self.usedspace = self.usedspace + bytemax

    def _onAxonHostFini(self):
        for axon in list(self.axons.values()):
            axon.fini()

    def makeAxonOpts(self):
        '''
        Make a configable dictionary from the current AxonHost options.

        Returns:
            dict: Configable dict of valid options which can be passed to a Axon()
        '''
        ret = {}
        for name, valu in self.getConfOpts().items():
            if name not in self._axonconfs:
                continue
            ret[name] = valu
        return ret

    def info(self):
        '''
        Return info for attempting to allocate clones and check health.
        '''
        usage = self.usage()
        return {
            'count': len(self.axons),
            'free': usage.get('free', 0),
            'used': usage.get('used', 0),
            'hostname': self.getConfOpt('axon:hostname'),
        }

    def getAxonHostStatus(self):
        '''
        Get status about the AxonHost and Axons it is hosting.

        Returns:
            (str, dict): Tufo of information about the axonhost and the axons.
        '''
        statsd = {
            'host:info': self.info(),
            'axons': [axon.getAxonStatus() for axon in list(self.axons.values())],
            'time': s_common.now()
        }
        return s_tufo.ephem('axonhost:status', self.iden, **statsd)

    def add(self, **opts):
        '''
        Add a new axon to the AxonHost.

        Args:
            **opts: kwarg values which supersede the defaults of the AxonHost when making the Axon.

        Examples:
            Add another Axon to the host with defaults::

                axfo = host.add()

        Returns:
            ((str, dict)): A Axon information tuple containing configuration and link data.
        '''
        iden = s_common.guid()

        fullopts = self.makeAxonOpts()
        fullopts['axon:iden'] = iden  # store iden as a specified option
        fullopts.update(opts)

        bytemax = fullopts.get('axon:bytemax')
        clone = fullopts.get('axon:clone')

        volinfo = s_thisplat.getVolInfo(self.datadir)

        free = volinfo.get('free')
        total = volinfo.get('total')
        maxsize = self.getConfOpt('axonhost:maxsize')

        if maxsize and (self.usedspace + bytemax) > maxsize:
            raise s_common.NotEnoughFree(mesg='Not enough free space on the AxonHost (due to axonhost:maxsize) to '
                                              'create the new Axon.',
                                         bytemax=bytemax, maxsize=maxsize, usedspace=self.usedspace)

        if (self.usedspace + bytemax) > free:
            raise s_common.NotEnoughFree(mesg='Not enough free space on the volume when considering the allocations'
                                              ' of existing Axons.',
                                         bytemax=bytemax, free=free, usedspace=self.usedspace)

        if bytemax > free:
            raise s_common.NotEnoughFree(mesg='Not enough free space on the volume to create the new Axon.',
                                         bytemax=bytemax, free=free)

        axondir = s_common.gendir(self.datadir, '%s.axon' % iden)

        s_common.jssave(fullopts, axondir, 'axon.opts')

        # FIXME fork
        axon = Axon(axondir, **fullopts)

        self.usedspace = self.usedspace + bytemax

        self.axons[iden] = axon

        if clone:
            self.cloneaxons.append(iden)

        return axon.axfo

    def usage(self):
        '''
        Return volume usage info.
        '''
        volinfo = s_thisplat.getVolInfo(self.datadir)
        return volinfo

class AxonMixin:
    '''
    The parts of the Axon which must be executed locally in proxy cases.
    ( used as mixin for both Axon and AxonCluster )
    '''
    @s_telepath.clientside
    def eatfd(self, fd):
        '''
        Consume the contents of a file object into the axon as a blob.

        Example:

            tufo = axon.eatfd(fd)

        '''

        hset = HashSet()
        iden, props = hset.eatfd(fd)

        blob = self.byiden(iden)
        if blob is not None:
            return blob

        fd.seek(0)

        sess = self.alloc(props.get('size'))

        byts = fd.read(10000000)
        retn = self.chunk(sess, byts)

        byts = fd.read(10000000)
        while byts:
            retn = self.chunk(sess, byts)
            byts = fd.read(10000000)

        return retn

    @s_telepath.clientside
    def eatbytes(self, byts):
        '''
        Consume a buffer of bytes into the axon as a blob.

        Example:

            tufo = axon.eatbytes(byts)

        '''
        hset = HashSet()

        hset.update(byts)
        iden, props = hset.guid()
        blob = self.byiden(iden)
        if blob is not None:
            return blob

        sess = self.alloc(props.get('size'))

        for chnk in s_common.chunks(byts, 10000000):
            blob = self.chunk(sess, chnk)

        return blob

class AxonCluster(AxonMixin, s_eventbus.EventBus):
    '''
    Present a singular axon API from an axon cluster.
    '''
    def __init__(self, svcprox):
        s_eventbus.EventBus.__init__(self)
        self.axons = {}
        self.saves = {}

        self.svcprox = svcprox
        self.svcprox.on('syn:svc:fini', self._onSvcFini)
        self.onfini(self.svcprox.fini)

    def _onSvcFini(self, mesg):
        svcfo = mesg[1].get('svcfo')
        if svcfo is None:
            return

        axon = self.axons.get(svcfo[0])
        if axon is None:
            return

        axon.fini()

    def has(self, htype, hvalu, bytag=axontag):
        '''
        Returns True if any of the axons in the cluster contain the given hash.

        Example:

            if not axapi.has('sha256',filehash):
                dostuff()

        '''
        dyntask = s_common.gentask('has', htype, hvalu)
        for svcfo, retval in self.svcprox.callByTag(bytag, dyntask):
            if retval:
                return True

        return False

    def byiden(self, iden, bytag=axontag):
        '''
        Get a axon:blob node by iden (superhash) value.

        Args:
            iden (str): Iden to look up.

        Returns:
            ((str, dict)): Blob tufo returned by the Axons cortex.
        '''
        dyntask = s_common.gentask('byiden', iden)
        for svcfo, retval in self.svcprox.callByTag(bytag, dyntask):
            if retval:
                return retval

        return None

    def _getSvcAxon(self, iden):

        svcfo = self.svcprox.getSynSvc(iden)
        if svcfo is None:
            return None

        axon = self.axons.get(iden)
        if axon is None:

            link = svcfo[1].get('link')
            if link is None:
                return None

            def onfini():
                self.axons.pop(iden, None)

            try:

                axon = s_telepath.openlink(link)
                self.axons[iden] = axon

                axon.onfini(onfini)

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
        dyntask = s_common.gentask('find', htype, hvalu)
        for svcfo, blobs in self.svcprox.callByTag(bytag, dyntask):

            if not blobs:
                continue

            try:

                axon = self._getSvcAxon(svcfo[0])
                if axon is None:
                    continue

                [b[1].__setitem__('.axon', svcfo[0]) for b in blobs]
                retblobs.extend(blobs)

            except Exception as e:
                logger.warning('AxonApi find: %s %s' % (svcfo[0], e))

        return retblobs

    def iterblob(self, blob):
        # try to use the blob they wanted, otherwise look it up again and iter.
        axon = None

        iden = blob[1].get('.axon')
        axon = self._getSvcAxon(iden)

        if axon is None:
            valu = blob[1].get('axon:blob:sha256')
            for byts in self.bytes('sha256', valu):
                yield byts
            return

        for byts in axon.iterblob(blob):
            yield byts

    def bytes(self, htype, hvalu, bytag=axontag):

        dyntask = s_common.gentask('find', htype, hvalu)
        for svcfo, blobs in self.svcprox.callByTag(bytag, dyntask):

            if not blobs:
                continue

            axon = self._getSvcAxon(svcfo[0])
            if axon is None:
                continue

            for byts in axon.bytes(htype, hvalu):
                yield byts

            return

    def wants(self, htype, hvalu, size, bytag=axontag):
        if self.has(htype, hvalu, bytag=bytag):
            return None
        return self.alloc(size, bytag=bytag)

    def alloc(self, size, bytag=axontag):
        '''
        Allocate a new block within an axon to save size bytes.

        Returns an iden to use for subsequent calls to axon.chunk()

        '''
        axons = self._getWrAxons(bytag=bytag)
        if not len(axons):
            raise s_common.NoWritableAxons(mesg='No Writeable axons found in AxonCluster', bytag=bytag)

        random.shuffle(axons)

        for axon in axons:
            iden = axon.alloc(size)
            self.saves[iden] = {'iden': iden, 'axon': axon}
            return iden

    def chunk(self, iden, byts):
        info = self.saves.get(iden)
        if info is None:
            s_common.NoSuchIden(iden)

        axon = info.get('axon')
        retn = axon.chunk(iden, byts)
        if retn is not None:
            self.saves.pop(iden, None)

        return retn

    def _getWrAxons(self, bytag=axontag):

        wraxons = []

        # FIXME cache this call for a few seconds
        dyntask = s_common.gentask('getAxonInfo')
        for svcfo, axfo in self.svcprox.callByTag(bytag, dyntask):

            if axfo[1]['opts'].get('axon:ro'):
                continue

            axon = self._getSvcAxon(svcfo[0])
            if axon is None:
                continue

            wraxons.append(axon)

        return wraxons

    def _waitWrAxons(self, count, timeout):

        # mostly used for unit test race elimination
        maxtime = time.time() + timeout
        while True:
            if time.time() >= maxtime:
                return False

            if len(self._getWrAxons()) >= count:
                return True

            time.sleep(0.1)

class Axon(s_config.Config, AxonMixin):
    '''
    An Axon acts as a binary blob store with hash based indexing/retrieval.
    '''
    def __init__(self, axondir, **opts):
        s_config.Config.__init__(self)

        self.inprog = {}
        self.axondir = s_common.gendir(axondir)

        self.clones = {}
        self.clonehosts = set()
        self.clonelock = threading.Lock()

        self.readyclones = set()                # iden of each clone added as it comes up
        self.clonesready = threading.Event()    # set once all clones are up and running
        self.poffs = {}

        self.axonbus = None

        self.setConfOpts(opts)

        self.iden = self.getConfOpt('axon:iden')
        self.tags = self.getConfOpt('axon:tags')

        # if we're a clone, we're read-only and have no clones
        if self.getConfOpt('axon:clone'):
            self.setConfOpt('axon:ro', 1)
            self.setConfOpt('axon:clones', 0)

        corepath = os.path.join(self.axondir, 'axon.db')
        self.core = s_cortex.openurl('sqlite:///%s' % corepath)
        self.core.setConfOpt('modules', (('synapse.models.axon.AxonMod', {}),))
        self.core.setConfOpt('caching', 1)

        self._fs_mkdir_root()  # create the fs root
        self.flock = threading.Lock()

        fd = s_common.genfile(axondir, 'axon.heap')

        self.link = None
        self.heap = s_heap.Heap(fd)
        self.dmon = s_daemon.Daemon()

        lisn = self.getConfOpt('axon:listen')
        if lisn:
            self.link = self.dmon.listen(lisn)

        self.axfo = (self.iden, {})

        self.axthrs = set()

        self.setAxonInfo('link', self.link)
        self.setAxonInfo('opts', self.getConfOpts())
        self.on('syn:conf:set', self._onSetConfigableValu)

        self.dmon.share('axon', self)

        # create a reactor to unwrap core/heap sync events
        self.syncact = s_reactor.Reactor()
        self.syncact.act('splice', self.core.splice)
        self.syncact.act('heap:sync', self.heap.sync)

        # wrap core/heap sync events as axon:sync events
        self.core.on('splice', self._fireAxonSync)
        self.heap.on('heap:sync', self._fireAxonSync)

        self.syncdir = None

        self.onfini(self.core.fini)
        self.onfini(self.heap.fini)
        self.onfini(self.dmon.fini)

        # if we're not a clone, create a sync dir
        if not self.getConfOpt('axon:clone'):
            dirname = s_common.gendir(axondir, 'sync')
            syncopts = self.getConfOpt('axon:syncopts')
            self.syncdir = s_persist.Dir(dirname, **syncopts)
            self.onfini(self.syncdir.fini)

            self.on('axon:sync', self.syncdir.add)

        self.axcthr = None

        # share last to avoid startup races
        busurl = self.getConfOpt('axon:axonbus')
        if busurl:
            logger.debug('[%s] Sharing self on AxonBus', self.iden)
            self.axonbus = s_service.openurl(busurl)
            self.onfini(self.axonbus.fini)

            props = {'link': self.link, 'tags': self.tags}
            self.axonbus.runSynSvc(self.iden, self, **props)
            logger.debug('[%s] Finding/making clones', self.iden)
            self.axcthr = self._fireAxonClones()

        self.onfini(self._onAxonFini)

    @staticmethod
    @s_config.confdef(name='axon')
    def _axon_confdefs():
        confdefs = (
            ('axon:ro', {'type': 'bool', 'defval': 0,
                         'doc': 'Axon Read-only mode. Prevents allocating new space for writing data to the heap file.',
                         }),
            ('axon:clone', {'type': 'bool', 'defval': 0,
                            'doc': 'Flag to indicate the axon is to be a clone axon or not. Not usually directly set'
                                   'by the user.',
                            }),
            ('axon:clone:iden', {'type': 'str', 'defval': '',
                                 'doc': 'Iden of the axon that this is a clone of (only applies to clones). Not usually'
                                        ' directly set by the user.'}),
            ('axon:clones', {'type': 'int', 'defval': 2,
                       'doc': 'Number of clones to make of this axon on the axonbus.', }),
            ('axon:axonbus', {'type': 'str', 'defval': '',
                       'doc': 'Axon servicebus used for making clones of a Axon.', }),
            ('axon:hostname', {'type': 'str', 'defval': s_thishost.get('hostname'),
                       'doc': 'Hostname associated with an Axon.', }),
            ('axon:listen', {'type': 'str', 'defval': 'tcp://0.0.0.0:0/axon',
                       'doc': 'Default listener URL for the axon', }),
            ('axon:tags', {'defval': (),
                           'doc': 'Tuple of tag values for the axon over a Axon servicebus.'}),
            ('axon:iden', {'type': 'str', 'defval': None,
                           'doc': 'Unique identifier for the axon. Not usually directly set by the user.'}),
            ('axon:syncopts', {'defval': {},
                               'doc': 'kwarg Options used when making a persistent sync directory.'}),
            ('axon:bytemax', {'type': 'int', 'defval': terabyte,
                              'doc': 'Max size of data this axon is allowed to store.'}),
        )
        return confdefs

    def _onSetConfigableValu(self, mesg):
        axfo = self.getAxonInfo()
        name = mesg[1].get('name')
        valu = mesg[1].get('valu')
        opts = axfo[1].get('opts')
        opts[name] = valu

    @s_common.firethread
    def _fireAxonClones(self):
        '''
        Find the clones for the current Axon on the AxonBus
        '''

        # If this axon is a clone, then don't try to make or find other clones
        if self.getConfOpt('axon:clone'):
            return

        clones = self.core.getTufosByProp('axon:clone')
        for axfo in clones:
            iden = axfo[1].get('axon:clone')
            host = axfo[1].get('axon:clone:host')

            self.clonehosts.add(host)

            self._initAxonClone(iden)

            # Wait for our clone to come online
            waiter = self.waiter(1, 'syn:axon:clone:ready')
            waiter.wait(60)

        self._findAxonClones()

    def _waitClonesReady(self, timeout=None):
        '''
        Wait for the "clonesready" event which is set during
        initialization once running/online clone count is full.
        '''
        self.clonesready.wait(timeout=timeout)
        return self.clonesready.is_set()

    def _addCloneReady(self, iden, axon):
        '''
        Add the clone iden and Axon to the ready list and potentially set the "clonesready" event.

        Args:
            iden (str): The Axon clone iden.
            axon (Axon): A Proxy to an Axon.

        Returns:
            None
        '''
        if iden in self.readyclones:
            return

        count = self.getConfOpt('axon:clones')
        with self.clonelock:
            self.clones[iden] = axon
            self.readyclones.add(iden)
            if len(self.readyclones) == count:
                self.clonesready.set()

    def _delCloneReady(self, iden):
        '''
        Remove the clone iden from the ready list and unset the "clonesready" event.

        Args:
            iden (str): Iden to remove.

        Returns:
            None
        '''
        if iden not in self.readyclones:
            return

        with self.clonelock:
            self.clones.pop(iden, None)
            self.readyclones.remove(iden)
            self.clonesready.clear()

    def _findAxonClones(self):
        '''
        Sleep/Loop attempting to find AxonHost instances to clone for us.
        '''
        while len(self.clones) < self.getConfOpt('axon:clones'):

            if self.isfini:
                break

            try:

                axfo = self._findAxonClone()
                if axfo is None:
                    time.sleep(1)
                    continue

                self._initAxonClone(axfo[0])

                waiter = self.waiter(1, 'syn:axon:clone:ready')
                waiter.wait(60)

            except Exception as e:  # pragma: no cover
                logger.exception('Axon %s (_findAxonClones)', self.iden)

    def _findAxonClone(self):

        myhost = self.getConfOpt('axon:hostname')
        bytemax = self.getConfOpt('axon:bytemax')

        dyntask = s_common.gentask('info')
        hostinfo = list(self.axonbus.callByTag('class.synapse.axon.AxonHost', dyntask))

        hostinfo = [h for h in hostinfo if h[1].get('free') > bytemax]
        hostinfo = [h for h in hostinfo if h[1].get('hostname') != myhost]

        def hostkey(x):
            used = x[1].get('used')
            count = x[1].get('count')
            return (count, used)

        for svcfo, ahinfo in sorted(hostinfo, key=hostkey):
            try:
                host = ahinfo.get('hostname')
                if host in self.clonehosts:
                    continue

                props = {'axon:clone': 1,
                         'axon:clones': 0,
                         'axon:clone:iden': self.iden,
                         'axon:bytemax': bytemax,
                         'axon:hostname': host,
                         }

                axfo = self.axonbus.callByIden(svcfo[0], 'add', **props)

                tufo = self.core.formTufoByProp('axon:clone', axfo[0], host=host)
                self.clonehosts.add(host)
                if not axfo:  # pragma: no cover
                    logger.error('{} Did not get a clone for {} from {}'.format(myhost, self.iden, host))
                return axfo

            except Exception as e:
                logger.exception('Axon %s, svc iden %s, host %s, props %s (_findAxonClone)',
                                 self.iden, svcfo[0], host, props)

    def _initAxonClone(self, iden):
        tufo = self.core.formTufoByProp('axon:clone', iden)

        poff = self.syncdir.getIdenOffset(iden)
        self.poffs[iden] = poff
        thr = self._fireAxonClone(iden, poff)
        self.axthrs.add(thr)

    @s_common.firethread
    def _fireAxonClone(self, iden, poff):
        '''
        This thread actually performs the sync operations from the source Axon
        to the clone axon.

        Args:
            iden (str): Destination clone axon iden
            poff (s_persist.Offset): The offset object for sourcing sync events
            for the destination Axon.
        '''

        with poff:

            while not self.isfini:

                try:

                    svcfo = self.axonbus.getSynSvcByName(iden)

                    if not svcfo:
                        time.sleep(0.3)
                        continue

                    link = svcfo[1].get('link')
                    if link is None:  # pragma: no cover
                        raise s_common.LinkErr('No Axon clone Link For: %s' % (iden,))

                    logger.debug('[%s] connecting too clone %s @ %s', self.iden, iden, link)

                    with s_telepath.openlink(link) as axon:

                        # This event is used to signal that the socket on the Proxy has
                        # gone away, so we can break out of our Perist items() loop.
                        sockevt = threading.Event()

                        def _onRunSockFini(mesg):
                            sockevt.set()

                        axon.on('tele:sock:runsockfini', _onRunSockFini)

                        self._addCloneReady(iden, axon)

                        self.fire('syn:axon:clone:ready', iden=iden)

                        off = poff.get()

                        for noff, item in self.syncdir.items(off):

                            if sockevt.is_set():
                                logger.warning('[%s] Breaking out of noff @ [%s] due to disconnect', self.iden, noff)
                                break

                            logger.debug('[%s] Syncing noff: [%s]', self.iden, noff)
                            axon.sync(item)
                            poff.set(noff)
                            logger.debug('[%s] Synced noff: [%s]', self.iden, noff)

                        # Cleanup
                        self._delCloneReady(iden)

                    logger.warning('[%s] Looping in _fireAxonClone inner while loop', self.iden)

                except Exception as e:  # pragma: no cover

                    logger.exception('Axon %s, clone iden %s (_fireAxonClone)', self.iden, iden)

                    if self.isfini:
                        break

                    time.sleep(1)

        self.poffs.pop(iden, None)
        logger.debug('Graceful exit for _fireAxonClone thread')

    def getAxonInfo(self):
        '''
        Return a dictionary of salient info about an axon.
        '''
        return self.axfo

    def getAxonStatus(self):
        '''
        Get runtime information for the current axon.

        Returns:
            ((None, dict)): A ephemeral Tufo of data about the current axon.
        '''
        statsd = {
            'heap:used': self.heap.heapSize(),
            'heap:atomsize': self.heap.atomSize(),
            'inprog': {k: dict(v) for k, v in list(self.inprog.items())},
            'clones:ready': self.clonesready.is_set(),
            'clones:clonesready': tuple(sorted(self.readyclones)),
            'clones:clonehosts': tuple(sorted(self.clonehosts)),
            'thrs:len': len(self.axthrs),
            'time': s_common.now(),
        }

        if self.syncdir:
            statsd['sync:size'] = self.syncdir.dirSize()
            statsd['sync:idens'] = tuple(sorted(self.syncdir.getOffsetIdens()))
            statsd['sync:poffs'] = {iden: poff.valu for iden, poff in list(self.poffs.items())}

        # Cleanup statsd from objects which will not serialize
        for v in statsd.get('inprog').values():
            v.pop('hashset', None)

        return s_tufo.ephem('axon:stats', self.iden, **statsd)

    def setAxonInfo(self, prop, valu):
        self.axfo[1][prop] = valu

    def find(self, htype, hvalu):
        '''
        Returns a list of blob tufos for hashes in the axon.

        Args:
            htype (str): Hash type.
            hvalu (str): Hash value.

        Examples:
            Find all blobs for a given md5sum::

                blobs = axon.find('md5', md5hash)

        Returns:
            list: List of tufos for a given hash value.
        '''
        return self.core.getTufosByProp('axon:blob:%s' % htype, valu=hvalu)

    def bytes(self, htype, hvalu):
        '''
        Yield chunks of bytes for the given hash value.

        Args:
            htype (str): Hash type.
            hvalu (str): Hash value.

        Examples:
            Get the bytes for a given guid and do stuff with them::

                for byts in axon.bytes('guid', axonblobguid):
                    dostuff(byts)


            Iteratively write bytes to a file for a given md5sum::

                for byts in axon.bytes('md5', md5sum):
                    fd.write(byts)

            Form a contiguous bytes object for a given sha512sum. This is not recommended for large files.::

                byts = b''.join((_byts for _byts in axon.bytes('sha512', sha512sum)))

        Notes:
            This API will raise an exception to the caller if the requested
            hash is not present in the axon. This is contrasted against the
            Axon.iterblob() API, which first requires the caller to first
            obtain an axon:blob tufo in order to start retrieving bytes from
            the axon.

        Yields:
            bytes:  A chunk of bytes for a given hash.

        Raises:
            NoSuchFile: If the requested hash is not present in the axon. This
            is raised when the generator is first consumed.
        '''
        blob = self.has(htype, hvalu)
        if blob:
            for byts in self.iterblob(blob):
                yield byts
        else:
            raise s_common.NoSuchFile(mesg='The requested blob was not found.',
                                      htype=htype, hvalu=hvalu)

    def iterblob(self, blob):
        '''
        Yield bytes blocks from the give blob until complete.

        Args:
            blob ((str, dict)):  axon:blob tufo to yield bytes from.

        Examples:
            Get the bytes from a blob and do stuff with them::

                for byts in axon.iterblob(blob):
                    dostuff(byts)

            Iteratively write bytes to a file for a given blob::

                fd = file('foo.bin','wb')
                for byts in axon.iterblob(blob):
                    fd.write(byts)

            Form a contiguous bytes object for a given blob. This is not recommended for large files.::

                byts = b''.join((_byts for _byts in axon.iterblob(blob)))

        Yields:
            bytes:  A chunk of bytes
        '''
        off = blob[1].get('axon:blob:off')
        size = blob[1].get('axon:blob:size')

        for byts in self.heap.readiter(off, size):
            yield byts

    def wants(self, htype, hvalu, size):
        '''
        Single round trip call to Axon.has() and possibly Axon.alloc().

        Args:
            htype (str): Hash type.
            hvalu (str): Hash value.
            size (int): Number of bytes to allocate.

        Examples:
            Check if a sha256 value is present in the Axon, and if not, create the node for a set of bytes::

                iden = axon.wants('sha256',valu,size)
                if iden != None:
                    for byts in chunks(filebytes,onemeg):
                        axon.chunk(iden,byts)

        Returns:
            None if the hvalu is present; otherwise the iden is returned for writing.
        '''
        if self.has(htype, hvalu):
            return None

        return self.alloc(size)

    def _fireAxonSync(self, mesg):
        self.fire('axon:sync', mesg=mesg)

    def sync(self, mesg):
        '''
        Consume an axon:sync event (only if we are a clone).
        '''
        if not self.getConfOpt('axon:clone'):
            raise s_common.NotSupported(mesg='Axon is not a Clone and cannot react to sync events')

        self.syncact.react(mesg[1].get('mesg'))

    def _onAxonFini(self):
        # join clone threads
        [thr.join(timeout=2) for thr in list(self.axthrs)]
        if self.axcthr is not None:
            self.axcthr.join(timeout=2)

    def alloc(self, size):
        '''
        Initialize a new blob upload context within this axon.

        Args:
            size (int): Size of the blob to allocate space for.

        Examples:
            Allocate a blob for a set of bytes and write it too the axon::

                iden = axon.alloc(len(byts))
                for b in chunks(byts,10240):
                    axon.chunk(iden,b)

        Returns:
            str: Identifier for a given upload.

        Raises:

        '''
        if self.getConfOpt('axon:clone'):
            raise s_common.NotSupported(mesg='Axon Is Clone - cannot allocate new blobs.')

        if self.getConfOpt('axon:ro'):
            raise s_common.NotSupported(mesg='Axon Is Read-Only - cannot allocate new blobs.')

        hsize = self.heap.heapSize()
        bytmax = self.getConfOpt('axon:bytemax')
        if (hsize + size) > bytmax:
            raise s_common.NotEnoughFree(mesg='Not enough free space on the heap to allocate bytes.',
                                         size=size, heapsize=hsize, bytemax=bytmax)

        iden = s_common.guid()
        off = self.heap.alloc(size)

        self.inprog[iden] = {'size': size, 'off': off, 'cur': off, 'maxoff': off + size, 'hashset': HashSet()}

        return iden

    def chunk(self, iden, byts):
        '''
        Save a chunk of a blob allocated with alloc().

        Args:
            iden (str): Iden to save bytes too
            byts (bytes): Bytes to write to the blob.

        Returns:
            ((str, dict)): axon:blob node if the upload is complete; otherwise None.

        Raises:
            NoSuchIden: If the iden is not in progress.
        '''
        info = self.inprog.get(iden)

        if info is None:
            raise s_common.NoSuchIden(iden)

        cur = info.get('cur')
        self.heap.writeoff(cur, byts)

        info['cur'] += len(byts)

        hset = info.get('hashset')
        hset.update(byts)

        # if the upload is complete, fire the add event
        if info['cur'] == info['maxoff']:

            self.inprog.pop(iden, None)

            off = info.get('off')
            iden, props = hset.guid()

            return self.core.formTufoByProp('axon:blob', iden, off=off, **props)

    def has(self, htype, hvalu):
        '''
        Check if the Axon has a given hash type/valu combination stored in it.

        Args:
            htype (str): Hash type.
            hvalu (str): Hash value.

        Examples:
            Check if a sha256 value is present::

                if not axon.has('sha256', shaval):
                    stuff()

            Check if a known superhash iden is present::

                if axon.has('guid', guidval):
                    stuff()

        Returns:
            ((str, dict)): axon:blob tufo if the axon has the hash or guid. None otherwise.
        '''
        if hvalu is None:
            logger.error('Hvalu must be provided.')
            return
        if htype == 'guid':
            tufo = self.core.getTufoByProp('axon:blob', hvalu)
        else:
            tufo = self.core.getTufoByProp('axon:blob:%s' % htype, hvalu)
        if tufo:
            return tufo

    def byiden(self, iden):
        '''
        Get a axon:blob node by iden (superhash) value.

        Args:
            iden (str): Iden to look up.

        Returns:
            ((str, dict)): Blob tufo returned by the Axons cortex.
        '''
        return self.core.getTufoByProp('axon:blob', iden)

    def fs_create(self, path, mode):
        '''
        Forms an axon:path node and sets its properties based on a given file mode.

        Args:
            path (str):  Path to form.
            mode (int): Path mode.

        Examples:
            Creating a directory::

                axon.fs_create('/mydir', 0o775)

            Creating a file ::

                axon.fs_create('/mydir/myfile', 0x81B4)

        Returns:
            None
        '''
        normed, props = self.core.getPropNorm('axon:path', path)

        dirn = None
        ppath = props.get('dir')

        if ppath:
            dirn = self._getDirNode(ppath)

        attr = Axon._fs_new_file_attrs(ppath, mode)
        with self.flock:
            filefo = self.core.formTufoByProp('axon:path', path, **attr)

        if filefo[1].get('.new') and dirn is not None:
            self.core.incTufoProp(dirn, 'st_nlink', 1)

        return 0

    def fs_getattr(self, path):
        '''
        Return the file attributes for a given file path.

        Args:
            path (str): Path to look up.

        Examples:
            Get the attributes for a given file::

                axon.fs_getattr('/foo/bar/baz.faz')

        Returns:
            dict: Attribute dictionary.
        '''
        path = self._fs_normpath(path)
        tufo = self.core.getTufoByProp('axon:path', path)
        # Inconsistent exception raising between this and fs_getxattr
        return Axon._fs_tufo2attr(tufo)

    def fs_getxattr(self, path, name):
        '''
        Return a file attribute value for a given file path and attr name.

        Args:
            path (str): Path to look up.
            name (str): Attribute name to retrieve.

        Examples:
            Get the size of a file::

                axon.fs_getxattr('/foo/bar/baz.faz', 'st_size')

        Returns:
            Requested attribute value, or None if the attribute does not exist.

        Raises:
            NoSuchData if the requested path does not exist.
        '''
        if name not in _fs_attrs:
            raise s_common.NoSuchData()

        path = self._fs_normpath(path)
        tufo = self.core.getTufoByProp('axon:path', path)
        if tufo:
            return tufo[1].get('axon:path:%s' % name)

        raise s_common.NoSuchData()

    def fs_mkdir(self, path, mode):
        '''
        Creates a new directory at the given path.

        Args:
            path (str): Path to create.
            mode (int): Mode for any created path nodes.

        Example:

            axon.fs_mkdir('/mydir', 0o775)

        Returns:
            None

        Raises:
            FileExists: If the path already exists.
        '''
        normed, props = self.core.getPropNorm('axon:path', path)

        dirn = None
        ppath = props.get('dir')

        if ppath:
            dirn = self._getDirNode(ppath)

        attr = Axon._fs_new_dir_attrs(ppath, mode)
        with self.flock:
            tufo = self.core.formTufoByProp('axon:path', path, **attr)
        if tufo and not tufo[1].get('.new'):
            raise s_common.FileExists()

        if dirn is not None:
            self.core.incTufoProp(dirn, 'st_nlink', 1)

    def _getDirNode(self, path):
        '''
        Get the axon:path node for a directory.

        Args:
            path (str): Path to retrieve

        Returns:
            ((str, dict)): axon:path node.

        Raises:
            NoSuchDir: If the path does not exist or if the path is a file.
        '''

        node = self.core.getTufoByProp('axon:path', path)
        if node is None:
            raise s_common.NoSuchDir()

        if not Axon._fs_isdir(node[1].get('axon:path:st_mode')):
            raise s_common.NoSuchDir()

        return node

    def fs_read(self, path, size, offset):
        '''
        Reads a file.

        Args:
            path (str): Path to read
            size (int): Number of bytes to read.
            offset (int): File offset to retrieve.

        Examples:
            Get the bytes of a file::

                byts = axon.fs_read('/dir/file1', 100, 0)

        Returns:
            bytes: Bytes read from the path.

        Raises:
            NoSuchEntity: If the path does not exist.
        '''
        tufo = self.core.getTufoByProp('axon:path', path)
        if not tufo:
            raise s_common.NoSuchEntity()
        bval = tufo[1].get('axon:path:blob')
        blob = None

        if bval:
            blob = self.core.getTufoByProp('axon:blob', bval)

        if not blob:
            return b''

        boff = blob[1].get('axon:blob:off')
        blob[1]['axon:blob:off'] = boff + offset  # the offset of the blob in the axon + the offset within the file
        blob[1]['axon:blob:size'] = size  # number of bytes that the OS asks for

        return b''.join(self.iterblob(blob))

    def fs_readdir(self, path):
        '''
        Reads a directory and gets a list of files in the directory.

        Args:
            path (str): Path to get a list of files for.

        Examples:d
            Read the files in the root directory::

                files = axon.fs_readdir('/')

        Returns:
            list: List of files / folders under the path
        '''
        files = ['.', '..']

        attr = self.fs_getattr(path)
        if not Axon._fs_isdir(attr.get('st_mode')):
            raise s_common.NotSupported()

        tufos = self.core.getTufosByProp('axon:path:dir', path)
        for tufo in tufos:
            fpath = tufo[1].get('axon:path')
            fname = fpath.split('/')[-1]
            if fname:
                files.append(fname)

        return files

    def fs_rmdir(self, path):
        '''
        Removes a directory

        Args:
            path (str): Path to remove.

        Examples:
            Remove a directory::

                axon.fs_rmdir('/mydir')

        Returns:
            None

        Raises:
            NoSuchEntity: If the path does not exist.
            NotEmpty: If the path is not empty.
        '''
        tufo = self.core.getTufoByProp('axon:path', path)
        if not tufo:
            raise s_common.NoSuchEntity()

        nlinks = tufo[1].get('axon:path:st_nlink')
        if nlinks != 2:
            raise s_common.NotEmpty()

        parent = tufo[1].get('axon:path:dir')
        if parent:
            parentfo = self.core.getTufoByProp('axon:path', parent)
            self.core.incTufoProp(parentfo, 'st_nlink', -1)
            self.core.delTufo(tufo)

    def fs_rename(self, src, dst):
        '''
        Rename a file:

        Args:
            src (str): Full path to the source file.
            dst (str): Full path to teh destination.

        Examples:
            Rename a file::

                axon.fs_rename('/myfile', '/mycoolerfile')

        Returns:
            None

        Raises:
            NoSuchEntity: If the source does not exist.
            NoSuchDir: If the source or destination parent path does not exist.
            NotEmpty: If the destination already exists.
        '''

        _, srcprops = self.core.getPropNorm('axon:path', src)
        srcppath, srcfname = srcprops.get('dir'), srcprops.get('base')
        _, dstprops = self.core.getPropNorm('axon:path', dst)
        dstppath, dstfname = dstprops.get('dir'), dstprops.get('base')

        with self.flock:

            srcfo = self.core.getTufoByProp('axon:path', src)
            if not srcfo:
                raise s_common.NoSuchEntity()
            src_isdir = Axon._fs_isdir(srcfo[1].get('axon:path:st_mode'))

            psrcfo = self.core.getTufoByProp('axon:path', srcppath)
            if not (psrcfo and Axon._fs_isdir(psrcfo[1].get('axon:path:st_mode'))):
                raise s_common.NoSuchDir()

            pdstfo = self.core.getTufoByProp('axon:path', dstppath)
            if not (pdstfo and Axon._fs_isdir(pdstfo[1].get('axon:path:st_mode'))):
                raise s_common.NoSuchDir()

            # prepare to set dst props to what src props were
            dstprops = Axon._get_renameprops(srcfo)
            dstprops.update({'dir': dstppath})

            # create or update the dstfo node
            dstfo = self.core.formTufoByProp('axon:path', dst, **dstprops)
            dst_isdir = Axon._fs_isdir(dstfo[1].get('axon:path:st_mode'))
            dst_isemptydir = dstfo[1].get('axon:path:st_nlink', -1) == 2
            dstfo_isnew = dstfo[1].get('.new')
            if dst_isdir and not dst_isemptydir and not dstfo_isnew:
                raise s_common.NotEmpty()

            # all pre-checks complete

            if dstfo_isnew:
                # if a new file was created, increment its parents link count ??
                self.core.incTufoProp(pdstfo, 'st_nlink', 1)
            else:
                # Now update dstfo props
                self.core.setTufoProps(dstfo, **dstprops)

            # if overwriting a regular file with a dir, remove its st_size
            if src_isdir:
                self.core.delTufoProp(dstfo, 'st_size')
                self._fs_reroot_kids(src, dst)

            # Remove src and decrement its parent's link count
            self.core.delTufo(srcfo)
            self.core.incTufoProp(psrcfo, 'st_nlink', -1)

    def fs_truncate(self, path):
        '''
        Truncates a file by setting its st_size to zero.

        Args:
            path (str): Path to truncate.

        Examples:
            Truncate a file::

                axon.fs_truncate('/myfile')

        Returns:
            None

        Raises:
            NoSuchEntity: If the path does not exist.
        '''
        tufo = self.core.getTufoByProp('axon:path', path)
        if tufo:
            self.core.delTufoProp(tufo, 'blob')
            self.core.setTufoProps(tufo, st_size=0)
            return

        raise s_common.NoSuchEntity(mesg='File does not exist to truncate.', path=path)

    def fs_unlink(self, path):
        '''
        Unlink (delete) a file.

        Args:
            path (str): Path to unlink.

        Examples:
            Delete a file::

                axon.fs_unlink('/myfile')

        Returns:
            None

        Raises:
            NoSuchFile: If the path does not exist.
        '''
        tufo = self.core.getTufoByProp('axon:path', path)
        if not tufo:
            raise s_common.NoSuchFile()

        ppath = tufo[1].get('axon:path:dir')
        self.core.delTufo(tufo)

        parentfo = self.core.getTufoByProp('axon:path', ppath)
        if parentfo:
            self.core.incTufoProp(parentfo, 'st_nlink', -1)

    def fs_utimens(self, path, times=None):
        '''
        Change file timestamps (st_atime, st_mtime).

        Args:
            path (str): Path to file to change.
            times (tuple): Tuple containing two integers - st_atime and st_mtime.

        Examples:
            Set the timestamps to epoch 0::

                axon.fs_utimens('/myfile', (0, 0))

        Returns:
            None
        '''
        if not(type(times) is tuple and len(times) == 2):
            return

        st_atime = int(times[0])
        st_mtime = int(times[1])

        tufo = self.core.getTufoByProp('axon:path', path)
        if tufo:
            self.core.setTufoProps(tufo, st_atime=st_atime, st_mtime=st_mtime)
            return

        raise s_common.NoSuchEntity(mesg='Path does not exist.', path=path)

    def _fs_reroot_kids(self, oldroot, newroot):

        for child in self.core.getTufosByProp('axon:path:dir', oldroot):

            normed, props = self.core.getPropNorm('axon:path', child[1].get('axon:path'))
            cpath, cfname = props.get('dir'), props.get('base')
            cmode = child[1].get('axon:path:st_mode')

            newdst = '%s%s%s' % (newroot, '/', cfname)
            self.core.delTufo(child)
            child[1]['axon:path:dir'] = newroot
            child[1]['axon:path'] = newdst
            self.core.formTufoByTufo(child)

            # move the kids
            if Axon._fs_isdir(cmode):
                newroot = '%s/%s' % (newroot, cfname)
                self._fs_reroot_kids(normed, newroot)

    def _fs_update_blob(self, path, blobsize, blob):
        tufo = self.core.getTufoByProp('axon:path', path)
        if tufo:
            self.core.setTufoProps(tufo, st_size=blobsize, blob=blob)

    def _fs_normpath(self, path):
        normed, _ = self.core.getPropNorm('axon:path', path)
        return normed

    def _fs_mkdir_root(self):
        '''
        Makes the root ('/') axon:path node.
        '''
        attr = Axon._fs_new_dir_attrs(None, 0x1FD)
        del attr['dir']
        attr['base'] = ''
        self.core.formTufoByProp('axon:path', '/', **attr)

    @staticmethod
    def _fs_tufo2attr(tufo):

        if not tufo:
            raise s_common.NoSuchEntity()

        attrs = {}
        for attr in _fs_attrs:
            val = tufo[1].get('axon:path:%s' % attr)
            if val is not None:
                attrs[attr] = val

        return attrs

    @staticmethod
    def _get_renameprops(tufo):

        props = Axon._fs_tufo2attr(tufo)
        blob = tufo[1].get('axon:path:blob')
        if blob:
            props['blob'] = blob

        return props

    @staticmethod
    def _fs_isdir(mode):

        try:
            return stat.S_ISDIR(mode)
        except:
            return False

    @staticmethod
    def _fs_isfile(mode):

        try:
            return stat.S_ISREG(mode)
        except:
            return False

    @staticmethod
    def _fs_new_file_attrs(parent, mode):

        now = int(time.time())
        return {'st_ctime': now, 'st_mtime': now, 'st_atime': now, 'st_nlink': 1, 'st_size': 0, 'st_mode': (stat.S_IFREG | mode), 'dir': parent}

    @staticmethod
    def _fs_new_dir_attrs(parent, mode):

        now = int(time.time())
        return {'st_ctime': now, 'st_mtime': now, 'st_atime': now, 'st_nlink': 2, 'st_mode': (stat.S_IFDIR | mode), 'dir': parent}

def _ctor_axon(opts):
    '''
    A function to allow terse/clean construction of an axon from a dmon ctor.

    Args:
        opts (dict): Options dictionary used to make the Axon object. Requires a "datadir" value.

    Returns:
        Axon: Axon created with the opts.

    Raises:
        BadInfoBalu: If the "datadir" value is missing from opts.
    '''
    datadir = opts.pop('datadir', None)
    if datadir is None:
        raise s_common.BadInfoValu(name='datadir', valu=None, mesg='axon ctor requires "datadir":<path> option')

    return Axon(datadir, **opts)

s_dyndeps.addDynAlias('syn:axon', _ctor_axon)

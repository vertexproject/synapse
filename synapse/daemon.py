import os
import sys
import json
import yaml
import zlib
import types
import logging
import threading
import collections
import multiprocessing

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.link as s_link
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.registry as s_registry
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.scope as s_scope
import synapse.lib.config as s_config

import synapse.lib.socket as s_socket
import synapse.lib.msgpack as s_msgpack
import synapse.lib.reflect as s_reflect
import synapse.lib.service as s_service
import synapse.lib.session as s_session
import synapse.lib.threads as s_threads
import synapse.lib.thisplat as s_thisplat

from synapse.eventbus import EventBus

# TODO: bumpDmonFork(self, name, fini=True)

logger = logging.getLogger(__name__)

#def opendir(dirn):
    #'''
    #Construct a Daemon() instance using the given directory.
    #'''
    #dirn = s_commmon.gendir(dirn)

    #if not os.path.isdir(dirn)
    #conf = yaml.loads(

#def forkdmon(conf):
    #dmon = Daemon()

    #try:
        #dmon.loadDmonConf(conf)
    #except Exception as e:
        #logger.exception(e)
        #sys.exit(FORK_ERR_CONFIG)

    #dmon.main()
    #sys.exit(FORK_ERR_OK)

#def checkConfDict(conf):
    #for incl in conf.get('includes', ()):
        #path = os.path.expanduser(incl)
        #checkConfFile(path)

    #for name, subconf in conf.get('forks', ()):
        #checkConfDict(subconf)

#def checkConfFile(path):
    #with open(path, 'rb') as fd:
        #try:
            #conf = json.loads(fd.read().decode('utf8'))
        #except Exception as e:
            #raise s_common.BadJson('(%s): %s' % (path, e))

    #return checkConfDict(conf)

#class DmonConf:
    #'''
    #A mixin class for configuring a daemon by dict/json.

    #Note: it is assumed that DmonConf is mixed into a class
          #which inherits from EventBus.
    #'''
    #def __init__(self):
        #self.conf = {}
        #self.locs = {'dmon': self}
        #self.forks = {}

        #self.cellprocs = {}

        #self.forkperm = {}
        #self.evalcache = {}
        #self._fini_items = []

        #self.onfini(self._onDmonFini)

    #def dmoneval(self, url):
        #'''
        #Evaluate ( and cache ) a URL (or local var/ctor name).

        #This allows multiple instances of the same URL to resolve to the
        #same object.
        #'''
        #item = self.locs.get(url)

        #if item is None:
            #item = self.evalcache.get(url)

        #if item is None:
            #item = s_telepath.evalurl(url, locs=self.locs)
            #self.evalcache[url] = item

        #return item

    #def _onDmonFini(self):
        #for name in list(self.forks.keys()):
            #self.killDmonFork(name, perm=True)

        #for celldir, proc in list(self.cellprocs.items()):
            #proc.terminate()
            #proc.join(2)

        # reverse the ebus items to fini them in LIFO order
        #for item in reversed(self._fini_items):
            #item.fini()

        #self._fini_items = []

    #def _addConfValu(self, conf, prop):
        ##valu = conf.get(prop)
        #if valu is not None:
            #self.setDmonConf(prop, valu)

    #def setDmonConf(self, prop, valu):
        #self.conf[prop] = valu
        #self.fire('dmon:conf:set', prop=prop, valu=valu)
        #self.fire('dmon:conf:set:%s' % (prop,), prop=prop, valu=valu)

    #@s_common.firethread
    #def _joinDmonFork(self, name, conf, proc):
        #proc.join()

        #if proc.exitcode == FORK_ERR_CONFIG:
            #logger.error('fork config (%s) error!' % name)
            #return

        #if not self.forkperm.get(name):
            #self._fireDmonFork(name, conf)

    #def _fireDmonFork(self, name, conf):
        #proc = multiprocessing.Process(target=forkdmon, args=(conf,))

        #self.forks[name] = proc
        #proc.start()

        #self._joinDmonFork(name, conf, proc)

    #def killDmonFork(self, name, perm=False):
        #'''
        #Kill ( not gracefully ) a daemon fork process by name.
        #'''
        #self.forkperm[name] = perm

        #proc = self.forks.get(name)
        #if proc is not None:
            #proc.terminate()

    #def loadDmonConf(self, conf):
        #'''
        #{
            #'title':'The Foo Thing',

            #'vars':{
                #'foo':10,
                #'bar':["baz","faz"]
            #}

            #'forks':(
                #('name',{
                    ## nested config for forked dmon
                #},
            #),

            #'includes':(
                #'~/foo/config.json',
            #),

            #'cells':(
                #(<dirn>, <conf>),
            #),

            #'ctors':(
                #('baz', 'ctor://foo.bar.Baz()'),
                #('faz', 'ctor://foo.bar.Baz()', {'config':'woot'}),
                #('mybus', 'tcp://host.com/syn.svcbus'),
            #),

            #'services':(
                #('mybus',(
                    #('baz',{'tags':('foo.bar','baz')}),
                #),
            #),

            #'addons':(
                #('auth','tcp://host.com:8899/synauth'),
                #('logging','ctor://mypkg.mymod.MyLogger()'),
            #),
        #}
        #'''
        #with s_scope.enter({'dmon': self}):
            #return self._loadDmonConf(conf)

    #def _loadDmonConf(self, conf):

        #checkConfDict(conf)
        #self.locs.update(conf.get('vars', {}))

        ## handle forks first to prevent socket bind weirdness
        #for name, subconf in conf.get('forks', ()):
            #self._fireDmonFork(name, subconf)

        #title = conf.get('title')
        #if title is not None:
            #s_thisplat.setProcName('dmon: %s' % title)

        # handle explicit module load requests
        #for name, info in conf.get('modules', ()):
            #modu = s_dyndeps.getDynMod(name)
            #if modu is None:
                #logger.warning('dmon mod not loaded: %s', name)

        # handle includes next
        #for path in conf.get('includes', ()):
            #fullpath = os.path.expanduser(path)
            #try:
                #self.loadDmonFile(fullpath)
            #except Exception as e:
                #raise Exception('Include Error (%s): %s' % (path, e))

        # deploy any cells we have configured...
        #celldone = set()
        #for celldirn, cellconf in conf.get('cells', ()):

            #if celldirn in celldone:
                #raise Exception('Duplicate Cell Entry: %s' % (celldirn,))

            #logger.info('dmon starting cell: %s' % (celldirn,))

            #celldone.add(celldirn)

            #proc = s_cell.divide(celldirn, cellconf)
            #self.cellprocs[celldirn] = proc

        # once neuron cells are standardized, nearly everything else can go

        #configs = conf.get('configs', {})

        #for row in conf.get('ctors', ()):

            #copts = {}   # ctor options
            #if len(row) == 2:
                #name, url = row
            #elif len(row) == 3:
                #name, url, copts = row
            #else:
                #raise Exception('Invalid ctor row: %r' % (row,))

            #if url.find('://') == -1:
                # this is a (name,dynfunc,config) formatted ctor...
                #item = s_dyndeps.tryDynFunc(url, copts)
            #else:
                #item = self.dmoneval(url)

            #self.locs[name] = item
            #if isinstance(item, EventBus):
                # Insert ebus items in FIFO order
                #self._fini_items.append(item)

            # check for a ctor opt that wants us to load a config dict by name
            #cfgname = copts.get('config')
            #if cfgname is not None:
                #if not isinstance(item, s_config.Configable):
                    #raise Exception('dmon ctor: %s does not support configs' % name)

                #opts = configs.get(cfgname)
                #if opts is None:
                    #raise s_common.NoSuchConf(name=cfgname)

                #item.setConfOpts(opts)

            # check for a ctor opt that wants us to "flatten" several configs in order
            #cfgnames = copts.get('configs')
            #if cfgnames is not None:

                #if not isinstance(item, s_config.Configable):
                    #raise Exception('dmon ctor: %s does not support configs' % name)

                #opts = {}
                #for cfgname in cfgnames:

                    #cfgopts = configs.get(cfgname)
                    #if cfgopts is None:
                        #raise s_common.NoSuchConf(name=cfgname)

                    #opts.update(cfgopts)

                #item.setConfOpts(opts)

            # check for a match between config and ctor names
            #opts = configs.get(name)
            #if opts is not None:
                #item.setConfOpts(opts)

            #self.fire('dmon:conf:ctor', name=name, item=item)

        #for busname, svcruns in conf.get('services', ()):
        #for name,

        #for busname, svcruns in conf.get('services', ()):

            #svcbus = self.dmoneval(busname)
            #if svcbus is None:
                #raise s_common.NoSuchObj(name)

            #for svcname, svcopts in svcruns:

                #item = self.locs.get(svcname)
                #if item is None:
                    #raise s_common.NoSuchObj(svcname)

                #svcname = svcopts.get('name', svcname)
                #s_service.runSynSvc(svcname, item, svcbus, **svcopts)

    #def loadDmonJson(self, text):
        #conf = json.loads(text)
        #return self.loadDmonConf(conf)

    #def loadDmonFile(self, path):
        ##checkConfFile(path)
        #with open(path, 'rb') as f:
            ##text = f.read().decode('utf8')
        #return self.loadDmonJson(text)

#_onhelp_lock = threading.Lock()

#class OnHelp:
    #'''
    #A class used by Daemon to deal with on() handlers and filters.
    #'''
    #def __init__(self):
        #self.ons = collections.defaultdict(dict)

    #@s_threads.withlock(_onhelp_lock)
    #def addOnInst(self, sock, iden, filt):

        #filts = self.ons[sock]
        #if not filts:
            #def fini():
                ##self.ons.pop(sock, None)
            #sock.onfini(fini)

        #filts[iden] = filt
        #return

    #@s_threads.withlock(_onhelp_lock)
    #def delOnInst(self, sock, iden):

        #filts = self.ons.get(sock)
        #if filts is None:
            #return

        #filts.pop(iden, None)
        #if not filts:
            #self.ons.pop(sock, None)

    #def dist(self, mesg):

        #for sock, filts in list(self.ons.items()):

            #for filt in filts.values():

                #if any(True for (k, v) in filt if mesg[1].get(k) != v):
                    #continue

                #sock.tx(mesg)
                #break

class Daemon(EventBus):

    def __init__(self, dirn=None, conf=None):

        EventBus.__init__(self)

        self.dirn = dirn

        if self.dirn is not None:
            self.dirn = s_common.gendir(dirn)

        self.auth = None
        self.socks = {}     # sockets by iden
        self.shared = {}    # objects provided by daemon
        #self.reflect = {}   # objects reflect info by name

        self._dmon_ons = {}
        self._dmon_links = []   # list of listen links
        self._dmon_yields = set()

        #if pool is None:
            #pool = s_threads.Pool(size=8, maxsize=-1)

        #self.pool = pool
        self.plex = s_socket.Plex()
        #self.cura = s_session.Curator()

        self.onfini(self.plex.fini)
        #self.onfini(self.pool.fini)
        #self.onfini(self.cura.fini)

        self.plex.on('link:sock:init', self._onLinkSockInit)
        self.plex.on('link:sock:mesg', self._onLinkSockMesg)

        self.mesgfuncs = {}

        self.setMesgFunc('tele:syn', self._onTeleSynMesg)
        self.setMesgFunc('sock:gzip', self._onSockGzipMesg)

        self.setMesgFunc('tele:call', self._onTeleCallMesg)

        # for "client shared" objects...
        #self.setMesgFunc('tele:push', self._onTelePushMesg)
        #self.setMesgFunc('tele:retn', self._onTeleRetnMesg)

        #self.setMesgFunc('tele:on', self._onTeleOnMesg)
        #self.setMesgFunc('tele:off', self._onTeleOffMesg)

        self.setMesgFunc('tele:yield:fini', self._onTeleYieldFini)

        if self.dirn is not None:
            self._loadDmonYaml()
            self._loadSvcDir()

    def _loadDmonYaml(self):
        path = s_common.genpath(self.dirn, 'dmon.yaml')
        if os.path.isfile(path):
            conf = self.loadYamlPath(path)
            self.loadDmonConf(conf)

    def _loadSvcDir(self):

        path = s_common.gendir(self.dirn, 'services')
        for name in os.listdir(path):

            if name.startswith('.'):
                continue

            dirn = os.path.join(path, name)
            path = os.path.join(dirn, 'service.yaml')

            if not os.path.exists(path):
                raise s_exc.NoSuchFile(name=path)

            conf = self.loadYamlPath(path)

            kind = conf.get('type')

            ctor = s_registry.getService(kind)
            if ctor is None:
                raise s_exc.NoSuchSvcType(name=kind)

            subc = conf.get('config')
            item = ctor(dirn, conf=subc)

            self.share(name, item)

    def loadYamlPath(self, path):
        '''
        Load a dmon config dict from a yaml file path.
        '''

        with open(path, 'rb') as fd:
            byts = fd.read()
            return yaml.load(byts.decode('utf8'))

    def setUserAuth(self, auth):
        self.auth = auth

    def _onTeleYieldFini(self, sock, mesg):
        iden = mesg[1].get('iden')
        self._dmon_yields.discard(iden)

    def loadDmonConf(self, conf):
        '''
        Process a Daemon config dictionary.
        '''

        lisn = conf.get('listen')
        if lisn is not None:

            url = lisn.get('url')

            if url is not None:
                opts = lisn.get('opts', {})
                link = self.listen(url, **opts)

        for name in conf.get('modules', ()):
            try:
                pymod = s_dyndeps.getDynMod(name)
            except Exception as e:
                mesg = 'dmon module error (%s): %s' % (name, e)
                logger.exception(mesg)

    def setMesgFunc(self, name, func):
        self.mesgfuncs[name] = func

    def _onLinkSockInit(self, mesg):

        sock = mesg[1].get('sock')

        def onfini():
            self.socks.pop(sock.iden, None)

        sock.onfini(onfini)
        self.socks[sock.iden] = sock

    def _onLinkSockMesg(self, mesg):
        # THIS MUST NOT BLOCK THE MULTIPLEXOR!
        s_glob.pool.call(self._runLinkSockMesg, mesg)

    def _runLinkSockMesg(self, event):
        sock = event[1].get('sock')
        mesg = event[1].get('mesg')

        self._distSockMesg(sock, mesg)

    def _distSockMesg(self, sock, mesg):

        func = self.mesgfuncs.get(mesg[0])
        if func is None:
            return

        try:

            func(sock, mesg)

        except Exception as e:
            logger.exception('exception in _runLinkSockMesg with mesg %s', mesg)

    #def _genChalSign(self, mesg):
        #'''
        #Generate a sign info for the chal ( if any ) in mesg.
        #'''
        #chal = mesg[1].get('chal')
        #if chal is None:
            #return {}

        #host = mesg[1].get('host')
        #if host is None:
            #return {}

        #return {}

    def _onSockGzipMesg(self, sock, mesg):
        data = zlib.decompress(mesg[1].get('data'))
        mesg = s_msgpack.un(data)
        self._distSockMesg(sock, mesg)

    def _onTeleSynMesg(self, sock, mesg):
        '''
        Handle a telepath tele:syn message which is used to setup
        a telepath session.
        '''
        jid = mesg[1].get('jid')

        # pass / consume protocol version information
        vers = mesg[1].get('vers', (0, 0))
        name = mesg[1].get('name')
        hisopts = mesg[1].get('opts', {})

        if hisopts.get('sock:can:gzip'):
            sock.set('sock:can:gzip', True)

        if vers[0] != s_telepath.telever[0]:
            info = s_common.errinfo('BadMesgVers', 'server %r != client %r' % (s_telepath.telever, vers))
            return sock.tx(s_common.tufo('job:done', jid=jid, **info))

        #iden = mesg[1].get('sess')
        #sess = self.cura.get(iden)

        ret = {
            #'sess': sess.iden,
            'vers': s_telepath.telever,
            'opts': {'sock:can:gzip': True},
        }

        #if name is not None:
            #ret['reflect'] = self.reflect.get(name)

        # send a nonce along for the ride in case
        # they want to authenticate for the session
        #if not sess.get('user'):
            #nonce = s_common.guid()
            #ret['nonce'] = nonce
            #sess.set('nonce', nonce)

        return sock.tx(s_common.tufo('job:done', jid=jid, ret=ret))

    #def _getOnHelp(self, name, evnt):
        #okey = (name, evnt)
        #onhelp = self._dmon_ons.get(okey)
        #if onhelp is None:
            #self._dmon_ons[okey] = onhelp = OnHelp()
            #return onhelp, True

        #return onhelp, False

    #def _onTeleOnMesg(self, sock, mesg):

        #try:
            # set the socket tx method as the callback
            #jid = mesg[1].get('jid')
            #ons = mesg[1].get('ons')
            #name = mesg[1].get('name')

            #item = self.shared.get(name)
            #if item is None:
                #raise s_common.NoSuchObj(name=name)

            #user = sock.get('syn:user')

            #func = getattr(item, 'on', None)
            #if func is None:
                #return sock.tx(s_common.tufo('job:done', jid=jid, ret=False))

            #self._reqUserAllowed(user, 'tele:call', name, 'on')

            #for evnt, ontups in ons: # (<evnt>, ( (<iden>,<filt>), ... ))
                #onhelp, new = self._getOnHelp(name, evnt)
                #if new:
                    #func(evnt, onhelp.dist)

                #for iden, filt in ontups:
                    #onhelp.addOnInst(sock, iden, filt)

            #return sock.tx(s_common.tufo('job:done', jid=jid, ret=True))

        #except Exception as e:
            #errinfo = s_common.excinfo(e)
            #sock.tx(s_common.tufo('job:done', jid=jid, err=errinfo.get('err'), errinfo=errinfo))

    #def _onTeleOffMesg(self, sock, mesg):
        # set the socket tx method as the callback
        #try:

            #jid = mesg[1].get('jid')
            #evnt = mesg[1].get('evnt')
            #name = mesg[1].get('name')
            #iden = mesg[1].get('iden')

            #item = self.shared.get(name)
            #if item is None:
                #raise s_common.NoSuchObj(name=name)

            #onhelp, new = self._getOnHelp(name, evnt)
            #onhelp.delOnInst(sock, iden)

            #return sock.tx(s_common.tufo('job:done', jid=jid, ret=True))

        #except Exception as e:
            ##errinfo = s_common.excinfo(e)
            #sock.tx(s_common.tufo('job:done', jid=jid, err=errinfo.get('err'), errinfo=errinfo))

    #def _reqUserAllowed(self, user, *perms):
        #if not self._isUserAllowed(user, *perms):
            #perm = ':'.join(perms)
            #logger.warning('userauth denied: %s %s' % (user, perm))
            #raise s_common.NoSuchRule(user=user, perm=perm)

    #def _isUserAllowed(self, user, *perms):

        #if self.auth is None:
            #return True

        ## If they have no user raise
        #if user is None:
            #raise s_common.NoAuthUser()

        #perm = ':'.join(perms)
        #return self.auth.isUserAllowed(user, perm)

    def _onTeleCallMesg(self, sock, mesg):

        # tele:call - call a method on a shared object

        jid = mesg[1].get('jid')
        sid = mesg[1].get('sid')

        # check if the socket knows about their auth
        # ( most likely via SSL client cert )
        user = sock.get('syn:user')

        with s_scope.enter({'dmon': self, 'sock': sock, 'syn:user': user, 'syn:auth': self.auth}):

            try:

                name = mesg[1].get('name')

                item = self.shared.get(name)
                if item is None:
                    raise s_common.NoSuchObj(name)

                task = mesg[1].get('task')
                meth, args, kwargs = task

                if meth[0] == '_':
                    raise s_common.NoSuchMeth(meth)

                #self._reqUserAllowed(user, 'tele:call', name, meth)

                func = getattr(item, meth, None)
                if func is None:
                    raise s_common.NoSuchMeth(meth)

                #logger.debug('Executing %s/%r for [%r]', jid, func, user)
                ret = func(*args, **kwargs)
                #logger.debug('Done executing %s', jid)

                # handle generator returns specially
                if isinstance(ret, types.GeneratorType):

                    iden = s_common.guid()

                    txwait = threading.Event()

                    # start off set...
                    txwait.set()

                    self._dmon_yields.add(iden)
                    sock.tx(s_common.tufo('tele:yield:init', jid=jid, iden=iden))

                    # FIXME opt
                    maxsize = 100000000
                    def ontxsize(m):
                        size = m[1].get('size')
                        if size >= maxsize:
                            txwait.clear()
                        else:
                            txwait.set()

                    try:

                        sock.onfini(txwait.set)
                        sock.on('sock:tx:size', ontxsize)

                        for item in ret:

                            txwait.wait()

                            # check if we woke due to fini
                            if sock.isfini:
                                break

                            sock.tx(s_common.tufo('tele:yield:item', iden=iden, item=item))
                            if iden not in self._dmon_yields:
                                break

                    finally:
                        sock.off('sock:tx:size', ontxsize)
                        self._dmon_yields.discard(iden)
                        sock.tx(s_common.tufo('tele:yield:fini', iden=iden))

                    return

                sock.tx(s_common.tufo('job:done', jid=jid, ret=ret))

            except Exception as e:
                errinfo = s_common.excinfo(e)
                sock.tx(s_common.tufo('job:done', jid=jid, err=errinfo.get('err'), errinfo=errinfo))

    def listen(self, linkurl, **opts):
        '''
        Create and run a link server by url.

        Example:

            link = dmon.listen('tcp://127.0.0.1:8888')

        Notes:

            * Returns the parsed link tufo

        '''
        link = s_link.chopLinkUrl(linkurl)
        link[1].update(opts)

        relay = s_link.getLinkRelay(link)

        sock = relay.listen()

        self.plex.addPlexSock(sock)

        self._dmon_links.append(link)
        return link

    def links(self):
        '''
        Return a list of the link tufos the Daemon is listening on.
        '''
        return list(self._dmon_links)

    def share(self, name, item):
        '''
        Share an object via the telepath protocol.

        Args:
            name (str): Name of the shared object
            item (object): The object to share over telepath.
        '''
        self.shared[name] = item
        #self.reflect[name] = s_reflect.getItemInfo(item)

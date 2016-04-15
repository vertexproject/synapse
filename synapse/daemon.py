import json
import logging
import traceback
import collections
import multiprocessing

import synapse.link as s_link
import synapse.lib.pki as s_pki
import synapse.lib.socket as s_socket
import synapse.lib.service as s_service
import synapse.lib.threads as s_threads
import synapse.lib.thisplat as s_thisplat

import synapse.cortex as s_cortex
import synapse.crypto as s_crypto
import synapse.telepath as s_telepath

from synapse.eventbus import EventBus

from synapse.common import *

# TODO: bumpDmonFork(self, name, fini=True)

logger = logging.getLogger(__name__)

def forkdmon(conf):
    dmon = Daemon()
    dmon.loadDmonConf(conf)
    dmon.main()

class DmonConf:
    '''
    A mixin class for configuring a daemon by dict/json.

    Note: it is assumed that DmonConf is mixed into a class
          which inherits from EventBus.
    '''
    def __init__(self):
        self.conf = {}
        self.locs = {'dmon':self}
        self.forks = {}

        self.forkperm = {}

        self.onfini( self._onDmonFini )

    def _onDmonFini(self):
        for name in list(self.forks.keys()):
            self.killDmonFork(name,perm=True)

    def _addConfValu(self, conf, prop):
        valu = conf.get(prop)
        if valu != None:
            self.setDmonConf(prop,valu)

    def setDmonConf(self, prop, valu):
        self.conf[prop] = valu
        self.fire('dmon:conf:set', prop=prop, valu=valu)
        self.fire('dmon:conf:set:%s' % (prop,), prop=prop, valu=valu)

    @firethread
    def _joinDmonFork(self, name, conf, proc):
        proc.join()
        if not self.forkperm.get(name):
            self._fireDmonFork(name,conf)

    def _fireDmonFork(self, name, conf):
        proc = multiprocessing.Process(target=forkdmon, args=(conf,))

        self.forks[name] = proc

        proc.start()

        self._joinDmonFork(name,conf,proc)

    def killDmonFork(self, name, perm=False):
        '''
        Kill ( not gracefully ) a daemon fork process by name.
        '''
        self.forkperm[name] = perm

        proc = self.forks.get(name)
        if proc != None:
            proc.terminate()

    def loadDmonConf(self, conf):
        '''
        {
            'title':'The Foo Thing',

            'vars':{
                'foo':10,
                'bar':["baz","faz"]
            }

            'forks':(
                ('name',{
                    # nested config for forked dmon
                },
            ),

            'includes':(
                '~/foo/config.json',
            ),

            'ctors':(
                ('baz','ctor://foo.bar.Baz()'),
                ('mybus','tcp://host.com/syn.svcbus'),
            ),

            'services':(
                ('mybus',(
                    ('baz',{'tags':('foo.bar','baz')}),
                ),
            ),
        }
        '''
        self.locs.update( conf.get('vars',{}) )

        # handle forks first to prevent socket bind weirdness
        for name,subconf in conf.get('forks',()):
            self._fireDmonFork(name,subconf)

        title = conf.get('title')
        if title != None:
            s_thisplat.setProcName('dmon: %s' % title)

        # handle includes next
        for path in conf.get('includes',()):
            fullpath = os.path.expanduser(path)
            self.loadDmonFile(fullpath)

        self._addConfValu(conf,'poolsize')

        for name,url in conf.get('ctors',()):

            item = s_telepath.evalurl(url,locs=self.locs)
            self.locs[name] = item

            self.fire('dmon:conf:ctor', name=name, item=item)

        for busname,svcruns in conf.get('services',()):
            svcbus = self.locs.get(busname)
            if svcbus == None:
                raise NoSuchObj(name)

            for svcname,svcopts in svcruns:
                item = self.locs.get(svcname)
                if item == None:
                    raise NoSuchObj(svcname)

                tags = svcopts.get('tags',())
                svcname = opts.get('name',svcname)

                s_service.runSynSvc(svcname, item, svcbus, tags=tags)

    def loadDmonJson(self, text):
        conf = json.loads(text)
        return self.loadDmonConf(conf)

    def loadDmonFile(self, path):
        text = open(path,'rb').read().decode('utf8')
        return self.loadDmonJson(text)

class Daemon(EventBus,DmonConf):

    def __init__(self, core=None, pool=None):
        EventBus.__init__(self)
        DmonConf.__init__(self)

        if core == None:
            core = s_cortex.openurl('ram:///')

        self.socks = {}     # sockets by iden
        self.shared = {}    # objects provided by daemon
        self.pushed = {}    # objects provided by sockets

        self._dmon_links = []   # list of listen links

        if pool == None:
            pool = s_threads.Pool(size=8, maxsize=-1)

        self.pki = s_pki.PkiStor(core)

        self.pool = pool
        self.core = core
        self.plex = s_socket.Plex()

        self.onfini( self.plex.fini )
        self.onfini( self.pool.fini )

        self.on('link:sock:init', self._onLinkSockInit )
        self.plex.on('link:sock:mesg', self._onLinkSockMesg )

        self.mesgfuncs = {}

        self.setMesgFunc('tele:syn', self._onTeleSynMesg )

        self.setMesgFunc('tele:skey', self._onTeleSkeyMesg )
        self.setMesgFunc('tele:call', self._onTeleCallMesg )

        # for "client shared" objects...
        self.setMesgFunc('tele:push', self._onTelePushMesg )
        self.setMesgFunc('tele:retn', self._onTeleRetnMesg )

        self.setMesgFunc('tele:on', self._onTeleOnMesg )
        self.setMesgFunc('tele:off', self._onTeleOffMesg )

    def loadDmonConf(self, conf):
        DmonConf.loadDmonConf(self,conf)

        for name,opts in conf.get('share',()):
            asname = opts.get('name',name)

            item = self.locs.get(name)
            if item == None:
                raise NoSuchObj(name)

            if opts.get('onfini'):
                self.onfini(item.fini)

            self.share(asname,item)

        # process a few daemon specific options
        for url in conf.get('listen',()):
            self.listen(url)

    def _onTelePushMesg(self, sock, mesg):

        jid = mesg[1].get('jid')
        name = mesg[1].get('name')

        def onfini():
            self.pushed.pop(name,None)

        sock.onfini(onfini)

        self.pushed[name] = sock
        return sock.tx( tufo('job:done', jid=jid) )

    def _onTeleRetnMesg(self, sock, mesg):
        # tele:retn - used to pump a job:done to a client
        suid = mesg[1].get('suid')
        if suid == None:
            return

        dest = self.socks.get(suid)
        if dest == None:
            return

        dest.tx( tufo('job:done', **mesg[1]) )

    def setMesgFunc(self, name, func):
        self.mesgfuncs[name] = func

    def _onLinkSockInit(self, event):

        sock = event[1].get('sock')
        sock.on('link:sock:mesg', self._onLinkSockMesg )

        def onfini():
            self.socks.pop(sock.iden,None)

        sock.onfini(onfini)
        self.socks[ sock.iden ] = sock

        self.plex.addPlexSock(sock)

    def _onLinkSockMesg(self, event):
        # THIS MUST NOT BLOCK THE MULTIPLEXOR!
        self.pool.call( self._runLinkSockMesg, event )

    def _runLinkSockMesg(self, event):
        sock = event[1].get('sock')
        mesg = event[1].get('mesg')

        func = self.mesgfuncs.get(mesg[0])
        if func == None:
            return

        try:

            func(sock,mesg)

        except Exception as e:
            traceback.print_exc()
            logger.error('_runLinkSockMesg: %s', e )

    def _genChalSign(self, mesg):
        '''
        Generate a sign info for the chal ( if any ) in mesg.
        '''
        chal = mesg[1].get('chal')
        if chal == None:
            return {}

        host = mesg[1].get('host')
        if host == None:
            return {}

        iden = self.pki.getIdenByHost(host)
        if iden == None:
            return {}

        cert = self.pki.getTokenCert(iden)
        sign = self.pki.genByteSign(iden,chal)

        return {'cert':cert,'sign':sign}

    def _onTeleSynMesg(self, sock, mesg):
        '''
        Handle a telepath tele:syn message which is used to setup
        a telepath session.
        '''
        jid = mesg[1].get('jid')
        sid = mesg[1].get('sid')
        host = mesg[1].get('host')

        ret = self._genChalSign(mesg)

        relay = sock.get('relay')

        pki = relay.getLinkProp('pki')
        if pki:
            # we require PKI client auth
            cert = mesg[1].get('cert')
            if cert == None:
                return sock.tx(tufo('job:done', jid=jid, err='NoPkiCert'))

            tokn = self.pki.loadCertToken(cert)
            if tokn == None:
                return sock.tx(tufo('job:done', jid=jid, err='BadPkiCert'))

            chal = os.urandom(16)

            sock.set('syn:pki:chal:byts',chal)
            sock.set('syn:pki:chal:token',tokn)

            ret['chal'] = chal

        return sock.tx( tufo('job:done', jid=jid, ret=ret) )

    def _onTeleOnMesg(self, sock, mesg):
        # set the socket tx method as the callback

        # FIXME perms

        jid = mesg[1].get('jid')
        name = mesg[1].get('name')
        events = mesg[1].get('events')

        item = self.shared.get(name)
        if item == None:
            raise NoSuchObj(name)

        on = getattr(item,'on',None)
        if on == None:
            return sock.tx( tufo('job:done', jid=jid, ret=False) )

        for evt in events:
            on(evt,sock.tx)

        def onfini():
            for evt in events:
                item.off(evt, sock.tx)

        sock.onfini(onfini)

        return sock.tx( tufo('job:done', jid=jid, ret=True) )

    def _onTeleOffMesg(self, sock, mesg):
        # set the socket tx method as the callback

        # FIXME perms

        evt = mesg[1].get('evt')
        jid = mesg[1].get('jid')
        name = mesg[1].get('name')

        item = self.shared.get(name)
        if item == None:
            raise NoSuchObj(name)

        off = getattr(item,'off',None)
        if off == None:
            return sock.tx( tufo('job:done', jid=jid, ret=False) )

        off(evt,sock.tx)
        return sock.tx( tufo('job:done', jid=jid, ret=True) )

    def _onTeleSkeyMesg(self, sock, mesg):

        # tele:skey - client specified shared key, encrypted to server w/pki

        jid = mesg[1].get('jid')
        iden = mesg[1].get('iden')
        byts = mesg[1].get('skey')

        skey = self.pki.decToIden(iden,byts)
        if skey == None:
            return sock.tx(tufo('job:done', jid=jid, err='BadPkiSkey'))

        xform = s_crypto.Rc4Skey( skey )

        sock.tx(tufo('job:done', jid=jid, ret=True))

        sock.addSockXform( s_crypto.Rc4Skey(skey) )

    def _onTeleCallMesg(self, sock, mesg):

        # tele:call - call a method on a shared object

        jid = mesg[1].get('jid')
        sid = mesg[1].get('sid')

        perm = sock.get('perm')

        with s_threads.ScopeLocal(perm=perm, dmon=self, sock=sock):

            try:

                name = mesg[1].get('name')

                item = self.shared.get(name)
                if item == None:
                    # is it a pushed object?
                    pushsock = self.pushed.get(name)
                    if pushsock != None:
                        # pass along how to reply
                        mesg[1]['suid'] = sock.iden
                        return pushsock.tx( mesg )

                    raise NoSuchObj(name)

                task = mesg[1].get('task')
                meth,args,kwargs = task

                func = getattr(item,meth,None)
                if func == None:
                    raise NoSuchMeth(meth)

                ret = func(*args,**kwargs)

                sock.tx( tufo('job:done', jid=jid, ret=ret) )

            except Exception as e:
                sock.tx( tufo('job:done', jid=jid, **excinfo(e)) )

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
        sock.on('link:sock:init', self.dist )

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

        Example:

            dmon.share('foo', Foo())

        '''
        self.shared[name] = item


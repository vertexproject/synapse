import os
import time
import errno
import socket
import logging
import threading
import collections

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.link as s_link
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.kv as s_kv
import synapse.lib.net as s_net
import synapse.lib.fifo as s_fifo
import synapse.lib.config as s_config
#import synapse.lib.socket as s_socket
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads
#import synapse.lib.thishost as s_thishost

import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.vault as s_vault
import synapse.lib.crypto.tinfoil as s_tinfoil

logger = logging.getLogger(__file__)

'''

Session Layer Messages:

    ('init', {'sess':<buid>, 'cert':<byts>, 'skey':<byts>})
    ('fini', {'sess':<buid>, 'data':<byts>})
    ('xmit', {'sess':<buid>, 'chan': <buid>, 'data': <mesg>})

'''

class NodeProxy(s_eventbus.EventBus):
    '''
    '''

    def __init__(self, addr):

        s_eventbus.EventBus.__init__(self)

        self.plex = Plex() #TODO: global plex...

        self.sess = os.random(16)
        self.skey = os.random(16)

        self.tinh = s_tinfoil.TinFoilHat(self.skey)

        self.lock = threading.Lock()
        self.ready = threading.Event()

        self._runConnLoop()

        self.rxque = s_queue.Queue()

    def _runConnLoop(self):

        self.ready.clear()

        def func(ok, retn):

            if not ok:
                logger.warning('socket connect error: %s' % retn)
                s_glob.sched.insec(1, self._runConnLoop)
                return

            with self.lock:
                self.sock = sock

#class UserSess(s_net.Link):

    #def __init__(self, sdef, cert):

        #self.stok = stok

        #self.sdef = sdef

        #self.cert = cert
        #self.tokn = s_msgpack.un(cert[0])

        #self.prikey = s_rsa.PriKey.load(self.tokn[1].get('rsa:pubkey'))

        #self.buid = os.urandom(16)
        #self.skey = s_tinfoil.newkey()

    #def linked(self):
        #print('UserSessLinked')

    #def handlers(self):
        #return {
            #'xmit': self._onMesgXmit,
        #}

#class NodeUser:

    #def __init__(self, svcfo, tokn):
        #self.tokn = tokn
        #self.svcfo = svcfo

        #self.lock = threading.Lock()
        #self.ready = threading.Event()

    #def _userSessCtor(

    #def _onLinkFini(self):

#class UserSess(s_net.Link):
    #def __init__(self,

#class Sess(s_net.Proto):
    #'''
    #The "session layer" neuron protocol implements auth/crypto.
    #'''
    #def __init__(self, node):
        ##s_net.Proto.__init__(self)
        #self.node = node

    #def _onMesgInit(self, mesg):

        #cert = s_crypto.loadcert(mesg[1].get('cert'))

        # check user cert...

        # get the sess key, check signature, and decrypt
        #skey = mesg[1].get('skey')

        # check if sess exists and belongs to another...
        #buid = mesg[1].get('sess')

        #self.node.setSessKey(buid, skey)

        #sess = self.node._initNodeSess(link, buid, skey)

    #def _onMesgXmit(self, mesg):

        #buid = mesg[1].get('sess')
        #byts = mesg[1].get('data')

        #sess = self.node.getNodeSess(link, buid)
        #if sess is None:
            #return

        #byts = sess.tinh.dec(byts)
        #if byts is None:
            #logger.warning('xmit message decryption failure')
            #return

        #sess.rx(s_msgpack.un(byts))

    #def #_onMesgFini(self, mesg):

        #buid = mesg[1].get('sess')

        # TODO: auth/sign this...
        #sess = self.node.getNodeSess(link, buid)
        ##if sess is None:
        #    return

        # if they can't encrypt the data "bye", they're not real...
        #byeb = mesg[1].get('data')
        #if sess.dec(byeb) != b'bye':
        #    return

        #sess.fini()

class CellSess(s_net.Link):
    '''
    Implements the Cell side of the session link.
    '''
    def __init__(self, node):

        s_net.Link.__init__(self)

        self.node = node

        # we dunno yet..
        self.buid = None
        self.tinh = None

        #skey = node.getSessKey(buid)

        #self.tinh = s_tinfoil.TinFoilHat(skey)

    def handlers(self):
        return {
            'init': self._onMesgInit,
            'xmit': self._onMesgXmit,
        }

    def _onMesgInit(self, mesg):

        print('CELL INIT: %r' % (mesg,))

        skey = mesg[1].get('skey')

        self.buid = mesg[1].get('sess')
        self.rxtinh = s_tinfoil.TinFoilHat(skey)

        s_net.Link.tx(self, ('init', {'sess': self.buid, 'skey': b'hehe'}))

    def _onMesgXmit(self, mesg):
        sess = mesg[1].get('sess')
        data = mesg[1].get('data')

        data = self.rxtinh.dec(data)
        if data is None:
            logger.warning('invalid data decrypt: %r' % (mesg,))

        imsg = s_msgpack.un(data)
        print('CELL GOT XMIT: %r' % (imsg,))

    #def _onMesgFini(self, mesg):
    #def _onMesgXmit(self, mesg):

        #self.onfini(self._onSessFini)

    #def _onSessFini(self):

class Cell(s_config.Config):
    '''
    A Cell is a micro-service in a neuron cluster.
    '''
    _def_port = 0

    def __init__(self, dirn, conf=None):

        s_config.Config.__init__(self)

        self.dirn = dirn
        s_common.gendir(dirn)

        # config file in the dir first...
        self.loadConfPath(self.path('config.json'))

        if conf is not None:
            self.setConfOpts(conf)

        self.reqConfOpts()

        self.plex = s_net.Plex()

        self.kvstor = s_kv.KvStor(self.path('cell.lmdb'))

        self.kvinfo = self.kvstor.getKvDict('cell:info')

        # open our vault
        self.vault = s_vault.Vault(self.path('vault.lmdb'))

        self.boot = self._loadBootFile()

        # setup our certificate and private key
        user = self.get('user') # do we have our user saved?

        # persist the session keys for later resume...
        self.skeys = self.kvstor.getKvLook('sess:keys')
        self.sessions = s_eventbus.BusRef()

        #self.preLisnHook()

        host = self.getConfOpt('host')
        port = self.getConfOpt('port')

        if port == 0:
            port = self.kvinfo.get('port', port)

        ctor = self.getSessCtor()
        addr = self.plex.listen((host, port), ctor)
        print('ADDR: %r' % (addr,))

        # save the port so it can be semi-stable...
        self.kvinfo.set('port', addr[1])

    def getSessCtor(self):
        def ctor():
            return CellSess(self)
        return ctor

    def get(self, prop, defval=None):
        '''
        Get a persistent property of the Cell.
        '''
        return self.kvinfo.get(prop, defval=None)

    def set(self, prop, valu):
        '''
        Set a persistent property of the Cell.
        '''
        return self.kvinfo.set(prop, valu)

    #def addEndpHand(self, name, func):
    #def addEndpFunc(self, name, func):
    #def addEndpIter(self, name, func):

    #def preLisnHook(self):
        # may be used to manipulate config before listen
        #pass

    def _loadBootFile(self):
        '''
        ./node.boot is a msgpack bootstrap dict
        ( it is deleted one loaded the first time )
        '''
        path = self.path('cell.boot')
        if not os.path.isfile(path):
            return None

        with io.open(path, 'rb') as fd:
            byts = fd.read()

        os.unlink(path)

        boot = s_msgpack.un(byts)
        self._initFromBoot(boot)

        return boot

    def _initFromBoot(self, boot):

        # get and trust the root user cert
        root = boot.get('root')
        if root is not None:
            self.vault.addSignerCert(root)

        auth = boot.get('auth')
        if auth is not None:
            self.set('user', auth[0])
            self.vault.addUserAuth(auth, signer=True)

    #def _initNodeSess(self):
        #return NodeSess(self)

    def setSessKey(self, buid, skey):
        self.skeys.setraw(buid, skey)

    def getSessKey(self, buid):
        self.skeys.getraw(buid)

    #def getNodeSess(self, link, buid):

        #sess = self.sessions.get(buid)
        #if sess is None:

            # check for a saved session key
            #skey = self.getSessKey(buid)
            #if skey is None:
                #return None

            #sess = self._initNodeSess(link, buid, skey)

        #return sess

    #def _initNodeSess(self, link, buid, skey):
        # init a new Sess link with the given skey
        #sess = Sess(self, link, buid, skey)
        #self.sessions.put(buid, sess)
        #return sess

    #def getNodeAddr(self):
        #'''
        #Return a (host, port) address for the Node.

        #Returns:
            #((str,int)): Host and TCP port tuple.
        #'''
        #return self.addr

    def path(self, *paths):
        '''
        Join a path relative to the cell persistence directory.
        '''
        return os.path.join(self.dirn, *paths)

    #def _noAuthMesgBeat(self, sock, mesg):
    #def _noAuthMesgAuth(self, sock, mesg):

    @staticmethod
    @s_config.confdef(name='cell')
    def _getNodeConf():
        return (
            ('host', {'defval': '0.0.0.0', 'req': 1,
                'doc': 'The host to bind'}),

            ('port', {'defval': 0, 'req': 1,
                'doc': 'The TCP port to bind (defaults to dynamic)'}),
        )

nodeport = 65521

class Node(Cell):
    '''
    A neuron node is the "master cell" for a neuron cluster.
    '''
    def __init__(self, dirn):
        Cell.__init__(self, dirn)

    #def preLisnHook(self):
        # we would prefer a default port...
        #if self.getConfOpt('port') == 0:
            #self.setConfOpt('port', nodeport)

    @staticmethod
    @s_config.confdef(name='node')
    def _getNodeConf():
        return (
            ('host', {'defval': '0.0.0.0', 'req': 1,
                'doc': 'The host to bind'}),

            ('port', {'defval': nodeport, 'req': 1,
                'doc': 'The TCP port to bind (defaults to %d)' % nodeport}),
        )

#class Chan(Link):
    #FIXME make chan fini *not* fini linkdown
    #def __init__(self, cell, link):

#class Hemi(Node):
    #'''
    #A Hemi (Hemisphere) is a super-node for a local Node cluster.
    #'''
    #def __init__(self, conf):

        #Node.__init__(self, conf)

        #hemi = self.getConfOpt('hemi')

        #byts = self.kvinfo.get('cacert')

        #self.cakey = self.kvvault.getCaKey(hemi)
        #self.cacert = self.kvvault.getCaCert(hemi)

        #if self.cakey is None:
            #self.cakey, self.cacert = self.kvvault.genSelfCa(hemi)

        #self.addLinkFunc('node:boot', self._onNodeBootMesg)

    #def _onNodeBootMesg(self, link, mesg):
        # an un-authenticated message to enroll a new service

#class NodeUser(s_net.Proto):

    #def __init__(self, nsvc, tokn):
        #self.nsvc = nsvc
        #self.tokn = tokn
#
        #self.plex = s_net.Plex()

        #self.sessproto = SessProto

    #@s_net.protorecv('retn')
    #def _onMesgRecvRetn(self, link, mesg):

#class Endp:

#class Bridge:
#class Endp:

#class Service:

    #@staticmethod
    #@s_config.confdef(name='neuron')
    #def _getNeurConf():
        #return (
            #('neur:dir', {'type': 'str', 'req': 1, 'doc': 'The working directory for this node'}),
            #('neur:links', {'defval': [], 'doc': 'A list of link entries: url or (url,{})'}),
            #('neur:listen', {'doc': 'A list of link entries: url or (url,{})'}),
            #('neur:fifo:conf', {'doc': 'A nested config dict for our own fifo'}),

            #('neur:dend:ctors', {'doc': 'A list of (dynf,conf) tuples for the dendrites to load'}),
        #)

class CellLink(s_net.Link):

    def __init__(self, prox):
        s_net.Link.__init__(self)
        self.prox = prox

    def handlers(self):
        return {
            'init': self._onMesgInit,
        }

    def _onMesgInit(self, mesg):
        print('INIT REPLY: %r' % (mesg,))
        self.tx(('CRYPTED', {'hehe': 'haha'}))

    def linked(self):

        print('LINKED')

        self.buid = os.urandom(16)
        self.skey = s_tinfoil.newkey()

        self.txhat = s_tinfoil.TinFoilHat(self.skey)

        mesg = ('init', {
                    'sess': self.buid,
                    'cert': self.prox.cert,
               })

        s_net.Link.tx(self, mesg)

        # bypass our xmit wrapping for init/fini
        #s_net.Link.tx(self, ('init', {'sess': self.buid, 'skey': self.skey}))

        #self.tx(('init',{'hi':'here'}))

    def tx(self, mesg):
        data = self.txhat.enc(s_msgpack.en(mesg))
        s_net.Link.tx(self, ('xmit', {'sess': self.buid, 'data': data}))

uservault = '~/.syn/vault.lmdb'

class NodeProxy:

    def __init__(self, user, path=uservault):

        self.user = user
        self.path = path

        self.host = user.split('@', 1)[1]

        with s_vault.shared(path) as vault:

            self.rkey = vault.getRsaKey(user)
            if self.rkey is None:
                raise s_exc.NoSuchUser(name=user, mesg='No RSA key in vault: %s' % (path,))

            self.cert = vault.getUserCert(user)
            if self.cert is None:
                raise s_exc.NoSuchUser(name=user, mesg='No cert in vault: %s' % (path,))

        self.ready = threading.Event()

        self._runConnLoop()

    def _runConnLoop(self):
        ctor = self.getLinkCtor()
        s_glob.plex.connect((self.host, nodeport), ctor)

    def getLinkCtor(self):
        def ctor():
            return CellLink(self)
        return ctor

def opennode(user, path=uservault):
    return NodeProxy(user, path=path)

def open(desc, path=uservault):
    '''
    Open a connection to a remote Cell.

    Args:
        desc (str): A <user>@<cluster>/<service> string.
        vault (synapse.lib.crytpo.vault.Vault): Crypto vault.

    Example:

        # open a single node by guid as user visi
        visi@cluster.vertex.link/6a1a8e828764696cb15f473d43174a1ac5bec83d70f74cbe4eb82f03e655099a

        # open a single node by service alias:
        visi@cluster.vertex.link/$auth

        # open a group of nodes by the user running the node
        visi@cluster.vertex.link/~axon

        # open a group of nodes by server side tag
        visi@cluster.vertex.link/#woot
    '''
    return nodecache.open(desc, vault=vault)

    #name =
    #svcn = desc.split('/
    #/~axon

#class NodeProxy:

if __name__ == '__main__':

    #plex = Plex()

    #os.mkdir('shit')

    #conf = {'dir': 'shit', 'hemi': 'vertex00'}

    node = Node('shit')

    path = 'fakevault.lmdb'

    with s_vault.shared(path) as vault:
        vault.genUserCert('visi@vertex00')

    opennode('visi@vertex00', path=path)

    #rkey, cert = node.genNodeUser(

    #cell=Cell('crap')

    #plex = Neuron(conf)
    #print('ADDR: %r' % (node.getNodeAddr(),))

    #def conn(ok, link):
        #print('CONN: %r %r' % (ok, link))
        #done.set()

    #def lisn(ok, link):
        #print('LISN: %r %r' % (ok, link))

    #plex.listen('0.0.0.0', 8686, func=lisn)
    #node.plex.connect(('127.0.0.1', 8686), func=conn)
    #plex.connect('127.0.0.1', 8989, func=conn)

    while True:
        time.sleep(1)
    #done.wait()

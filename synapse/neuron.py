import os
import time
import errno
import socket
import logging
import threading
import collections
import multiprocessing

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.link as s_link
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
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
#class CellPlex(

class SessBoss:
    '''
    Base class for session negotiation pieces.
    '''
    def __init__(self, cert, roots):
        self.cert = cert
        self.roots = roots

        self.key = cert.getkey()
        self.certbyts = cert.save()

    def decrypt(self, byts):
        return self.key.decrypt(byts)

    def valid(self, cert):
        return any([r.signed(cert) for r in self.roots])

class Cell(s_config.Config, SessBoss):
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
        if user is None:
            user = 'visi@vertex00'

        print('CELL USER: %r' % (user,))

        self.root = self.vault.genRootCert()

        cert = self.vault.genUserCert(user)
        roots = self.vault.getRootCerts()

        SessBoss.__init__(self, cert, roots)

        host = self.getConfOpt('host')
        port = self.getConfOpt('port')

        if port == 0:
            port = self.kvinfo.get('port', port)

        ctor = self.getLinkCtor()
        addr = self.plex.listen((host, port), ctor)
        print('ADDR: %r' % (addr,))

        # save the port so it can be semi-stable...
        self.kvinfo.set('port', addr[1])

    def getLinkCtor(self):

        def sess(chan):
            sess = Sess(chan, self, lisn=True)
            chan.onrx(sess.rx)
            sess.linked()

        def ctor(sock):
            return s_net.ChanPlex(sock, sess)

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

    def path(self, *paths):
        '''
        Join a path relative to the cell persistence directory.
        '''
        return os.path.join(self.dirn, *paths)

    @staticmethod
    @s_config.confdef(name='cell')
    def _getCellConf():
        return (

            ('ctor', {'req': 1,
                'doc': 'The path to the cell constructor'}),

            ('root', {
                'doc': 'The SHA256 of our neuron root cert (used for autoconf).'}),

            ('neuron', {
                'doc': 'The host name (and optionally port) of our neuron'}),

            ('host', {'defval': '0.0.0.0', 'req': 1,
                'doc': 'The host to bind'}),

            ('port', {'defval': 0, 'req': 1,
                'doc': 'The TCP port to bind (defaults to dynamic)'}),
        )

nodeport = 65521

class Neuron(Cell):
    '''
    A neuron node is the "master cell" for a neuron cluster.
    '''
    def __init__(self, dirn, conf=None):
        Cell.__init__(self, dirn, conf=conf)

    @staticmethod
    @s_config.confdef(name='node')
    def _getNodeConf():
        return (
            ('host', {'defval': '0.0.0.0', 'req': 1,
                'doc': 'The host to bind'}),

            ('port', {'defval': nodeport, 'req': 1,
                'doc': 'The TCP port to bind (defaults to %d)' % nodeport}),
        )

#class SessBase(s_net.Link):
class Sess(s_net.Link):

    def __init__(self, link, boss, lisn=False):

        s_net.Link.__init__(self, link)

        self.lisn = lisn    # True if we are the listener.
        self.boss = boss

        # if we fini, close the channel
        self.onfini(link.fini)

        self.txkey = s_tinfoil.newkey()
        self.txtinh = s_tinfoil.TinFoilHat(self.txkey)

        self.rxkey = None
        self.rxtinh = None

    def handlers(self):
        return {
            'cert': self._onMesgCert,
            'skey': self._onMesgSkey,
            'xmit': self._onMesgXmit,
        }

    def linked(self):

        if not self.lisn:
            byts = self.boss.certbyts
            self.link.tx(('cert', {'cert': byts}))

    def setRxKey(self, rxkey):
        self.rxkey = rxkey
        self.rxtinh = s_tinfoil.TinFoilHat(rxkey)

    def _tx_wrap(self, mesg):

        if self.rxtinh is None:
            raise s_exc.NotReady()

        data = self.txtinh.enc(s_msgpack.en(mesg))
        return ('xmit', {'sess': self.iden, 'data': data})

    def _onMesgXmit(self, mesg):

        if self.rxtinh is None:
            logger.warning('xmit message before rxkey')
            raise NotReady()

        data = mesg[1].get('data')

        newm = s_msgpack.un(self.rxtinh.dec(data))
        self.linkup.rx(newm)
        return


    def _onMesgSkey(self, mesg):

        data = mesg[1].get('data')
        skey = self.boss.decrypt(data)

        print('GOT RX KEY: %r' % (skey,))
        self.setRxKey(skey)

    def _onMesgCert(self, mesg):

        if self.lisn:
            self.link.tx(('cert', {'cert': self.boss.certbyts}))

        cert = s_vault.Cert.load(mesg[1].get('cert'))

        if not self.boss.valid(cert):
            clsn = self.__class__.__name__
            logger.warning('%s got bad cert (%r)' % (clsn, cert.iden(),))
            return

        # send back an skey message with our tx key
        data = cert.public().encrypt(self.txkey)
        mesg = ('skey', {'data': data})
        self.link.tx(mesg)

#class ConnSess(SessBase):

#class LisnSess(SessBase):

    #def _onMesgCert(self, mesg):


        # Process the init as normal...
        #return SessBase._onMesgCert(self, mesg)

class CellProxy(SessBoss):

    def __init__(self, user, path=s_vault.uservault):

        self.user = user
        self.path = path

        self.host = user.split('@', 1)[1]

        with s_vault.shared(path) as vault:

            cert = vault.getUserCert(user)

            if cert is None:
                raise s_exc.NoSuchUser(name=user, mesg='No cert in vault: %s' % (path,))

            roots = vault.getRootCerts()

        SessBoss.__init__(self, cert, roots)

        self.ready = threading.Event()

        self._runConnLoop()

    def _runConnLoop(self):
        ctor = self.getLinkCtor()
        s_glob.plex.connect((self.host, nodeport), ctor)

    def getLinkCtor(self):

        def onchan(chan):
            sess = Sess(chan, self, lisn=False)
            chan.onrx(sess.rx)
            sess.linked()

        def onsock(sock):

            plex = s_net.ChanPlex(sock, onchan)
            plex.open()

            return plex

        return onsock

def opencell(user, path=s_vault.uservault):
    return CellProxy(user, path=path)

def open(desc, path=s_vault.uservault):
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

def divide(dirn, conf=None):
    '''
    Create an instance of a Cell in a subprocess.
    '''
    # lets try to find his constructor...
    ctor = None

    if conf is not None:
        ctor = conf.get('ctor')

    path = s_common.genpath(dirn, 'config.json')

    if ctor is None and os.path.isfile(path):
        subconf = s_common.jsload(path)
        ctor = subconf.get('ctor')

    if ctor is None:
        raise ReqConfOpt(name='ctor')

    func = s_dyndeps.getDynLocal(ctor)
    if func is None:
        raise NoSuchCtor(name=ctor)

    proc = multiprocessing.Process(target=_cell_entry, args=(ctor, dirn, conf))
    proc.start()

    return proc

def _cell_entry(ctor, dirn, conf):

    try:

        dirn = s_common.genpath(dirn)
        func = s_dyndeps.getDynLocal(ctor)

        cell = func(dirn, conf)

        logger.info('cell divided: %s (%s)' % (ctor, dirn))

        cell.main()

    except Exception as e:
        logger.exception('_cell_entry: %s (%s)' % (ctor, e))

if __name__ == '__main__':


    try:

        path = 'fakevault.lmdb'

        with s_vault.shared(path) as connvault:

            #cert = connvault.genUserCert('visi@vertex00')
            #connvault.addSignerCert(cert)

            with s_vault.shared('shit/vault.lmdb') as lisnvault:
                root = lisnvault.genRootCert()
                auth = lisnvault.genUserAuth('visi@vertex00')

            #connvault.addRootCert(root)
            connvault.addUserAuth(auth)

        node = Cell('shit')
        print('NODE: %r' % (node,))

        opennode('visi@vertex00', path=path)

    except Exception as e:
        import traceback
        traceback.print_exc()

    while True:
        time.sleep(1)

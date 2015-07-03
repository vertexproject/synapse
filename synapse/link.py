import time
import threading
import importlib

import synapse.common as s_common
import synapse.crypto as s_crypto
import synapse.threads as s_threads

import synapse.links.tcp as s_tcp
import synapse.links.local as s_local

from synapse.eventbus import EventBus
from synapse.links.common import *

linkprotos = {
    'tcp':s_tcp.TcpProto(),
    #'local':s_local.LocalProto(),
}

def getLinkProto(name):
    '''
    Return a LinkProto for the given proto name.

    Example:

        proto = getLinkProto('tcp')
        sock = proto.initLinkSock( link )

    '''
    return linkprotos.get(name)

def addLinkProto(name, proto):
    '''
    Add a custom LinkProto by name.

    Example:

        class MyProto(LinkProto):
            # ...

        addLinkProto('mine',MyProto())

    '''
    linkprotos[name] = proto

def delLinkProto(name):
    '''
    Delete a LinkProto by name.

    Example:

        delLinkProto('mine')

    '''
    linkprotos.pop(name,None)

def reqLinkProto(name):
    '''
    Return a LinkProto by name or raise.
    '''
    proto = linkprotos.get(name)
    if proto == None:
        raise NoSuchLinkProto(name)
    return proto

def initLinkRelay(link):
    '''
    Construct a new LinkRelay for the link.

    Example:

        link = ('tcp',{'host':'1.2.3.4','port':80})
        relay = initLinkRelay(link)

    '''
    proto = reqLinkProto(link[0])
    return proto.initLinkRelay(link)

def initLinkSock(link):
    '''
    Initialize a new client Socket() for the link.

    Example:

        link = ('tcp',{'connect':('1.2.3.4',80)})
        sock = initLinkSock(link)

    '''
    proto = reqLinkProto(link[0])
    return proto.initLinkSock(link)

def initLinkFromUri(uri):
    '''
    Parse a URI string and return a link tuple.

    Example:

        link = initLinkFromUri('tcp://1.2.3.4:9999/')

    '''
    name = uri.split(':',1)[0]
    proto = reqLinkProto(name)
    return proto.initLinkFromUri(uri)

def reqValidLink(link):
    '''
    Raise an exception if the link is not configured correctly.
    '''
    proto = reqLinkProto(link[0])
    proto.reqValidLink(link)

class LinkClient(EventBus):
    '''
    A synapse link client.

    Notes:

        Mostly a base class for senses.

    '''
    def __init__(self, link):
        EventBus.__init__(self)

        self.link = link
        self.lock = threading.Lock()

        self.on('sockinit', self._onSockInit )
        self.onfini(self._finiLinkClient)

        self.sock = initLinkSock(self.link)

        if self.sock == None:
            raise Exception('Initial Link Failed: %r' % (self.link,))

        if link[1].get('trans'):
            self.sock.close()

    def sendAndRecv(self, name, **info):
        '''
        Send a message and receive a message transactionally.

        Example:

            resp = client.sendAndRecv( ('woot',{}) )

        Notes:

            * This API will reconnect as needed

        '''
        mesg = (name, info)
        with self.lock:
            while True:
                self._sendLinkMesg(mesg)
                ret = self.sock.recvobj()
                if ret == None:
                    continue

                # if our link has trans=True try to obey and be
                # transactional ( disconnect every time )
                if self.link[1].get('trans'):
                    self.sock.close()

                return ret

    def _finiLinkClient(self):
        self.sock.close()

    def _sendLinkMesg(self, mesg):
        sent = self.sock.sendobj(mesg)
        while not sent and not self.isfini:
            self._runReConnect()
            sent = self.sock.sendobj(mesg)

    def _onSockInit(self, event):
        sock = event[1].get('sock')
        rc4key = self.link[1].get('rc4key')
        if rc4key != None:
            prov = s_crypto.RC4Crypto(self.link)
            sock._setCryptoProv( prov )

    def _runReConnect(self):

        self.sock.close()

        self.sock = initLinkSock(self.link)
        if self.sock != None:
            self.fire('sockinit',sock=self.sock)
            return

        delay = self.link[1].get('delay',0)
        while self.sock == None and not self.isfini:
            time.sleep(delay)

            delaymax = self.link[1].get('delaymax',2)
            delayinc = self.link[1].get('delayinc',0.2)
            delay = min( delay + delayinc, delaymax )

            self.sock = initLinkSock(self.link)

        self.fire('sockinit',sock=self.sock)

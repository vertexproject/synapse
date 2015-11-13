'''
An RMI framework for synapse.
'''
import copy
import threading
import threading
import traceback

import synapse.link as s_link
import synapse.socket as s_socket
import synapse.eventbus as s_eventbus

from synapse.common import *
from synapse.compat import queue

def openurl(url):
    '''
    Construct a telepath proxy from a url.

    Example:

        foo = openurl('tcp://1.2.3.4:90/foo')

        foo.dostuff(30) # call remote method

    '''
    link = s_link.chopLinkUrl(url)
    relay = s_link.getLinkRelay(link)
    return Proxy(relay)

def openlink(link):
    '''
    Construct a telepath proxy from a link tufo.

    Example:

        foo = openlink(link)
        foo.bar(20)

    '''
    relay = s_link.getLinkRelay(link)
    return Proxy(relay)

class Method:

    def __init__(self, proxy, api):
        self.api = api
        self.proxy = proxy

    def __call__(self, *args, **kwargs):
        return self.proxy._tele_call( self.api, *args, **kwargs)

class Proxy:
    '''
    The telepath proxy provides "pythonic" access to remote objects.

    ( you most likely want openurl() or openlink() )
    '''
    def __init__(self, relay, sid=None):
        self.bus = s_eventbus.EventBus()

        self._tele_lock = threading.Lock()

        self._tele_sid = sid
        self._tele_with = {}        # tid:sock for with blocks
        self._tele_sock = None
        self._tele_relay = relay    # LinkRelay()

        # obj name is path minus leading "/"
        self._tele_obj = relay.link[1].get('path')[1:]

        self._init_main_sock()

        if sid == None:
            self._tele_sid = self._tele_syn()

    def _init_main_sock(self):

        if self.bus.isfini:
            return False

        if self._tele_sock != None:
            self._tele_sock.fini()

        waittime = 0
        self._tele_sock = None
        while self._tele_sock == None:

            self._tele_sock = self._tele_relay.connect()
            if self._tele_sock == None:
                time.sleep(waittime)
                waittime = min( waittime + 0.2, 2 )
                continue

    def _tele_call(self, api, *args, **kwargs):
        call = ( self._tele_obj, api, args, kwargs )
        mesg = self._tele_trans('tele:call', call=call)
        if mesg[0] != 'tele:call:ret':
            raise BadMesgResp(mesg[0])

        return retmesg(mesg)

    def _tele_syn(self):
        mesg = self._tele_trans('tele:syn')
        return retmesg(mesg)

    def _tele_trans(self, evt, **evtinfo):

        # carry out one send/recv transaction
        evtinfo['sid'] = self._tele_sid

        sock = self._get_with_sock()
        if sock != None:
            sock.fireobj(evt,**evtinfo)
            return sock.recvobj()

        with self._tele_lock:

            while not self._tele_sock.fireobj(evt,**evtinfo):
                self._init_main_sock()

            return self._tele_sock.recvobj()

    def _get_with_sock(self):
        thrid = threading.currentThread().ident
        return self._tele_with.get(thrid)

    def fini(self):
        self.bus.fini()
        self._tele_sock.fini()
        socks = list( self._tele_with.values() )
        [ sock.fini() for sock in socks ]

    def __enter__(self):
        thrid = threading.currentThread().ident
        sock = self._tele_relay.connect()
        self._tele_with[thrid] = sock
        return self

    def __exit__(self, exc, cls, tb):
        thrid = threading.currentThread().ident
        sock = self._tele_with.pop(thrid,None)
        if sock != None:
            sock.fini()

    def __getattr__(self, name):
        meth = Method(self, name)
        setattr(self,name,meth)
        return meth

    # some methods to avoid round trips...
    def __nonzero__(self):
        return True

    def __eq__(self, obj):
        return id(self) == id(obj)

    def __ne__(self, obj):
        return not self.__eq__(obj)


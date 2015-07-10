import weakref

import synapse.link as s_link
import synapse.daemon as s_daemon

class Daemon(s_daemon.Daemon):

    def __init__(self, statefd=None):
        self.chanlock = threading.Lock()
        self.chansocks = collections.defaultdict(set)
        s_daemon.Daemon.__init__(self, statefd=statefd)

        self.setMesgMethod('imp:imp', self._onMesgImpImp)
        self.setMesgMethod('imp:join', self._onMesgImpJoin)
        self.setMesgMethod('imp:leave', self._onMesgImpLeave)

    def _onMesgImpImp(self, sock, mesg):
        chan = mesg[1].get('chan')
        byts = msgpack.dumps(msg,use_bin_type=True)
        for s in self.chansocks.get(chan,()):
            s.sendall(byts)

    def _onMesgImpJoin(self, sock, mesg):
        chans = mesg[1].get('chans')
        [ self._putChanSock(chan,sock) for chan in chans ]

    def _onMesgImpLeave(self, sock, mesg):
        chans = mesg[1].get('chans')
        [ self._popChanSock(chan,sock) for chan in chans ]

    #def _putChanQue(self, chan, queue):
    #def _popChanQue(self, chan, queue):

    #def _putChanSock(self, chan, sock):

        #with self.chanlock:
            #socks = self.chansocks[chan]
            #size = len(socks)
#
            #socks.add(sock)

            # inform our upstreams of the new chan
            #if size == 0:
                #[ up.sendLinkMesg(mesg) for up in self.uplinks ]

    #def _popChanSock(self, chan, sock):
        #with self.chanlock:
            #socks = self.chansocks[chan]
            #socks.remove(sock)
            #if len(socks) == 0:
                #[ up.sendLinkMesg(mesg) for up in self.uplinks ]
                #self.chansocks.pop(chan,None)

def ImpulseChannel(EventBus):

    def __init__(self, client, chan):
        self.chan = chan
        self.client = client

    def fire(self, name, **info):
        '''
        Fire an impulse event on this channel.
        '''
        ret = EventBus.fire(name,**info)
        imp = (name,info)
        mesg = ('imp:imp',{'chan':self.chan,'imp':imp})
        self.client.sendLinkMesg(mesg)

#class ImpulseClient(s_link.LinkClient):
    #'''
    #ImpulseClient provides access to channelized event distribution.
    #'''
    #def __init__(self, link, linker=None):
        #s_link.LinkClient.__init__(self, link, linker=linker)
        #self.implock = threading.Lock()
        #self.impchans = {}
#
    #def getImpChan(self, name):
        #'''
        #Return a channel
        #'''
        #with self.implock:
            #chan = self.impchans.get(name)
            #if chan == None:
                #chan = ImpulseChannel(self,name)
                #self._sendImpJoin( name )
                #self.impchans[name] = chan
            #return chan

    #def _sendImpJoin(self, chan):
        #self.sendLinkMesg( ('imp:join', {'chan':chan}) )

    #def _sendImpLeave(self, chan):

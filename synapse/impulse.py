import msgpack

import synapse.common as s_common
import synapse.socket as s_socket
import synapse.threads as s_threads
import synapse.dispatch as s_dispatch

class Hub(s_socket.SocketPool):
    '''
    An impulse Hub is a broadcast service which forwards all
    provided events to all current listeners.

    Notes:
        * Any serializable objects may be rebroadcast.

    '''
    def __init__(self, statefd=None):
        s_socket.SocketPool.__init__(self,statefd=statefd)
        self.synOn('sockmesg', self._impSockMesg )

    def _impSockMesg(self, sock, mesg):
        # FIXME maybe socks should get marked "normal"
        # if they're not pump/listen ?

        # optimize for multi-send by serializing once.
        sid = sock.getSockId()
        byts = msgpack.dumps(mesg, use_bin_type=True)
        for sock in self.getPoolSocks():
            if sock.getSockInfo('listen'):
                continue
            if sock.getSockId() == sid:
                continue

            sock.sendall(byts)

import socket

import dendrite.socket as d_socket
import dendrite.threads as d_threads

class Server:
    '''
    Implements a socket server for use in dendrite Services.

    ( since connections will multi-plex msgs, use one thread per )
    '''
    def __init__(self, sockaddr, statefd, auditfd):
        self.lsock = socket.socket()
        self.lshut = False
        self.lthread = None

        self.sockaddr = sockaddr
        self.sockthreads = {}

    def runMainLoop(self):
        self.lsock.bind(self.sockaddr)
        self.lthread = d_threads.fireWorkThread( self._mainLoopThread )

    def _mainLoopThread(self):

    def waitForExit(self):
        '''
        Block until the server main loop returns.
        '''
        self.lthread.join()

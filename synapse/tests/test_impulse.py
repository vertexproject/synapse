import unittest
import threading

import synapse.socket as s_socket
import synapse.impulse as s_impulse

class ImpulseTest(unittest.TestCase):

    def test_impulse_hub(self):

        link = ('tcpd',{'host':'127.0.0.1','port':62269})

        hub = s_impulse.Hub()
        hub.runSockPool()

        evt = threading.Event()
        def letsrawk(sock):
            evt.set()

        hub.synOn('linksock',letsrawk)
        hub.runLink(link)

        evt.wait()

        sockaddr = ('127.0.0.1',62269)

        sock1 = s_socket.connect(sockaddr)
        sock2 = s_socket.connect(sockaddr)

        obj1 = ('asdf',1,2,3,4)
        sock1.sendSockMesg(obj1)

        obj2 = sock2.recvSockMesg()
        self.assertEqual(obj1,obj2)

        hub.synFireFini()

        sock1.close()
        sock2.close()

        

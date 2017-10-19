import threading

import synapse.lib.socket as s_socket
import synapse.lib.threads as s_threads

from synapse.tests.common import *


class ThreadsTest(SynTest):

    def test_threads_pool(self):

        def woot(x, y):
            return x + y

        with s_threads.Pool() as pool:

            with pool.task(woot, 20, 30) as task:
                pass

            self.true(task.waitfini(timeout=1))

    def test_threads_pool_wrap(self):

        evnt = threading.Event()
        def woot(x, y):
            evnt.set()
            return x + y

        with s_threads.Pool() as pool:
            pool.wrap(woot)(20, 30)
            self.true(evnt.wait(timeout=1))

    def test_threads_cancelable(self):

        sock1, sock2 = s_socket.socketpair()

        data = []
        def echoloop():
            with s_threads.cancelable(sock1.fini):
                byts = sock1.recv(1024)
                data.append(byts)
                sock1.sendall(byts)

        thr = s_threads.worker(echoloop)

        sock2.sendall(b'hi')
        self.eq(sock2.recv(1024), b'hi')

        thr.fini()
        thr.join()

        sock1.fini()
        sock2.fini()

    def test_threads_cantwait(self):

        self.true(s_threads.iMayWait())

        s_threads.iCantWait()

        self.false(s_threads.iMayWait())
        self.raises(MustNotWait, s_threads.iWillWait)

        del threading.currentThread()._syn_cantwait

        self.true(s_threads.iMayWait())

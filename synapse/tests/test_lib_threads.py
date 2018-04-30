import synapse.lib.socket as s_socket
import synapse.lib.threads as s_threads

from synapse.tests.common import *

def newtask(func, *args, **kwargs):
    return (func, args, kwargs)

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

    def test_threads_exception(self):
        data = {}

        def breakstuff():
            data['key'] = True
            return 1 / 0

        with self.getLoggerStream('synapse.lib.threads', 'error running task for') as stream:
            with s_threads.Pool() as pool:
                pool.call(breakstuff)
                self.true(stream.wait(2))

        self.true(data.get('key'))

    def test_threads_retnwait(self):
        with s_threads.RetnWait() as retn:
            def work():
                retn.retn(True)

            thrd = s_threads.worker(work)
            self.eq(retn.wait(timeout=1), (True, True))
            thrd.join()

        self.eq(retn.wait(timeout=1), (True, True))

        # no timeout
        with s_threads.RetnWait() as retn:
            def work():
                retn.retn(True)

            thrd = s_threads.worker(work)
            self.eq(retn.wait(), (True, True))
            thrd.join()

        self.eq(retn.wait(timeout=1), (True, True))

        # Let a wait() timeout
        with s_threads.RetnWait() as retn:
            def work():
                time.sleep(0.5)
                retn.retn(True)

            thrd = s_threads.worker(work)
            ok, retn = retn.wait(timeout=0.01)

            self.false(ok)
            self.eq(retn[0], 'TimeOut')

            thrd.join()

        with s_threads.RetnWait() as retn:
            def work():
                try:
                    1 / 0
                except ZeroDivisionError as e:
                    retn.errx(e)

            thrd = s_threads.worker(work)
            ret = retn.wait(timeout=1)
            thrd.join()
            self.false(ret[0])
            excfo = ret[1]
            self.istufo(excfo)
            self.eq(excfo[0], 'ZeroDivisionError')
            self.eq(excfo[1].get('msg'), 'division by zero')
            self.eq(excfo[1].get('name'), 'work')
            self.isin('test_lib_threads.py', excfo[1].get('file'))
            self.isin('line', excfo[1])  # Line may change
            self.isin('src', excfo[1])  # source for a inner function may not be available.

        # Test capture
        with s_threads.RetnWait() as retn:
            def work(a, b, c, callback):
                sum = a + b
                multiple = sum * c
                callback(sum, multiple, a=a, b=b, c=c)

            thrd = s_threads.worker(work, 1, 2, 3, retn.capture)
            ret = retn.wait(timeout=1)
            thrd.join()
            self.true(ret[0])
            self.eq(ret[1], ((3, 9), {'a': 1, 'b': 2, 'c': 3}))

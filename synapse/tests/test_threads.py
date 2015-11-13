import time
import unittest
import threading

import synapse.socket as s_socket
import synapse.threads as s_threads

from synapse.tests.common import *

#class Task:

    #def __init__(self, func, *args, **kwargs):
        #self.func = func
        #self.args = args
        #self.kwargs = kwargs

    #def __call__(self):
        #return self.func( *self.args, **self.kwargs )

def newtask(func,*args,**kwargs):
    return(func,args,kwargs)

class ThreadsTest(unittest.TestCase):

    def test_threads_pool(self):

        pool = s_threads.Pool()

        wait = TestWaiter( pool, 1, 'pool:work:fini' )

        def woot(x,y):
            return x + y

        pool.task(newtask(woot,20,30))

        wait.wait()
        pool.fini()

    def test_threads_perthread(self):

        data = dict(count=0)
        def woot(x,y=None):
            data['count'] += 1
            return (x,y)

        per = s_threads.PerThread()
        per.setPerCtor('woot',woot,10,y=20)

        def makeone():
            data['make'] = per.woot

        w1 = per.woot
        w2 = per.woot

        self.assertEqual( w1, (10,20) )
        self.assertEqual( id(w1), id(w2) )
        self.assertEqual( data['count'], 1 )

        thr = threading.Thread(target=makeone)
        thr.start()
        thr.join()

        w3 = data.get('make')
        self.assertEqual( w3, (10,20) )
        self.assertNotEqual( id(w1), id(w3) )


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
        self.assertEqual( sock2.recv(1024), b'hi')

        thr.fini()
        thr.join()

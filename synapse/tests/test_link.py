import io
import unittest
import threading

import synapse.link as s_link
import synapse.socket as s_socket

class LinkerTest(unittest.TestCase):

    def test_link_saveload(self):
        fd = io.BytesIO()
        linker = s_link.Linker(statefd=fd)

        linker.addLink('woot1',('tcp',{'host':'127.0.0.1','port':80}))
        linker.addLink('woot2',('tcp',{'host':'127.0.0.1','port':90}))

        linker.setLinkInfo('woot1','hehe',20)

        linker.setLinkInfo('woot2','hehe',20)
        linker.setLinkInfo('woot2','hehe',30)

        linker.synFireFini()

        fd.seek(0)

        linker = s_link.Linker(statefd=fd)

        self.assertEqual( linker.getLinkInfo('woot1','port'), 80 )
        self.assertEqual( linker.getLinkInfo('woot2','port'), 90 )

        self.assertEqual( linker.getLinkInfo('woot1','hehe'), 20 )
        self.assertEqual( linker.getLinkInfo('woot2','hehe'), 30 )

        linker.synFireFini()

        # we never tell him to run... :)

    def test_link_defmods(self):
        linker = s_link.Linker()
        self.assertIsNotNone( linker.getLinkModule('tcp') )
        self.assertIsNotNone( linker.getLinkModule('tcpd') )
        #self.assertIsNotNone( linker.getLinkMod('local') )
        #self.assertIsNotNone( linker.getLinkMod('locald') )
        linker.synFireFini()

    def test_link_invalid(self):

        linker = s_link.Linker()

        link = ('tcp',{})
        self.assertRaises( s_link.NoLinkProp, linker.checkLinkInfo, link )

        link = ('tcp',{'host':'_','port':80})
        self.assertRaises( s_link.BadLinkProp, linker.checkLinkInfo, link )

        linker.synFireFini()

    def test_link_runmain(self):

        evt = threading.Event()
        data = {'count':0,'sock':None}

        def linksock(sock):
            data['count'] += 1
            data['sock'] = sock
            evt.set()

        linker = s_link.Linker()
        linker.synOn('linksock',linksock)
        linker.runLinkMain()

        lisn = s_socket.listen(('127.0.0.1',0))
        addr = lisn.getsockname()

        link = ('tcp',{'host':'127.0.0.1','port':addr[1]})
        linker.addLink('woot',link)

        srvsock,cliaddr = lisn.accept()
        evt.wait()
        evt.clear()

        self.assertEqual( data.get('count'), 1 )

        # make him fire another....
        srvsock.close()
        data['sock'].close()

        srvsock,cliaddr = lisn.accept()
        evt.wait()
        evt.clear()

        self.assertEqual( data.get('count'), 2 )

        # but no more...
        linker.synFireFini()

        srvsock.close()
        data['sock'].close()

        lisn.close()

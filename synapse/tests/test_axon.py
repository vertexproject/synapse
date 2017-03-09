import io
import hashlib

import synapse.axon as s_axon
import synapse.daemon as s_daemon
import synapse.lib.heap as s_heap
import synapse.telepath as s_telepath
import synapse.lib.service as s_service

from synapse.tests.common import *

craphash = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
asdfhash = '6a204bd89f3c8348afd5c77c717a097a'

class AxonTest(SynTest):

    def test_axon_basics(self):
        with self.getTestDir() as axondir:

            axon = s_axon.Axon(axondir)

            self.assertFalse( axon.has('md5',craphash) )
            self.assertFalse( axon.has('md5',asdfhash) )

            iden0 = axon.alloc(8)

            self.assertIsNotNone( axon.chunk(iden0,b'asdfasdf') )

            self.assertTrue( axon.has('md5',asdfhash) )
            self.assertFalse( axon.has('md5',craphash) )

            byts = b''.join( axon.bytes('md5',asdfhash) )

            self.assertEqual(byts,b'asdfasdf')

            axon.fini()

            axon = s_axon.Axon(axondir)

            self.assertTrue( axon.has('md5',asdfhash) )
            self.assertFalse( axon.has('md5',craphash) )

            byts = b''.join( axon.bytes('md5',asdfhash) )

            self.assertEqual(byts,b'asdfasdf')

            self.assertIsNone(axon.wants('md5', asdfhash, 8))
            self.assertIsNotNone(axon.wants('md5', craphash, 8))

            axon.fini()

    def test_axon_sync(self):

        with self.getTestDir() as axondir:

            byts = os.urandom(128)
            bytsmd5 = hashlib.md5(byts).hexdigest()

            axon = s_axon.Axon(axondir,syncsize=64)

            iden = axon.alloc(128)
            for chnk in chunks(byts,10):
                blob = axon.chunk(iden,chnk)

            self.assertIsNotNone(blob)

            self.assertTrue( axon.has('md5',bytsmd5) )

            axon.fini()

    def test_axon_host(self):

        self.thisHostMustNot(platform='windows')

        with self.getTestDir() as datadir:

            with open(os.path.join(datadir,'foo'),'w') as fd:
                fd.write('useless file to skip')

            host = s_axon.AxonHost(datadir)
            usage = host.usage()

            props = {
                'syncmax':s_axon.megabyte * 10,
                'bytemax':s_axon.megabyte * 10,
            }

            axfo = host.add(**props)

            self.assertIsNotNone( usage.get('total') )

            axon = host.axons.get(axfo[0])

            iden = axon.alloc(100)
            blob = axon.chunk(iden,b'V'*100)

            self.assertIsNotNone(blob)

            self.assertTrue( axon.has( 'md5', blob[1].get('hash:md5') ) )
            self.assertTrue( axon.has( 'sha1', blob[1].get('hash:sha1') ) )
            self.assertTrue( axon.has( 'sha256', blob[1].get('hash:sha256') ) )

            host.fini()

            host = s_axon.AxonHost(datadir)
            axon = host.axons.get(axfo[0])

            self.assertTrue( axon.has( 'md5', blob[1].get('hash:md5') ) )
            self.assertTrue( axon.has( 'sha1', blob[1].get('hash:sha1') ) )
            self.assertTrue( axon.has( 'sha256', blob[1].get('hash:sha256') ) )

            props = {
                'syncmax':s_axon.megabyte * 10,
            }
            self.assertRaises(NotEnoughFree, host.add, **props)

            host.fini()

    def test_axon_host_clone(self):

        self.thisHostMustNot(platform='windows')

        busurl = 'local://%s/axons' % guid()

        dmon = s_daemon.Daemon()
        dmon.listen(busurl)

        dmon.share('axons', s_service.SvcBus(), fini=True)

        with self.getTestDir() as datadir:

            dir0 = gendir(datadir,'host0')
            dir1 = gendir(datadir,'host1')
            dir2 = gendir(datadir,'host2')

            opts = {
                'axonbus':busurl,
            }

            host0 = s_axon.AxonHost(dir0,hostname='host0',**opts)
            host1 = s_axon.AxonHost(dir1,hostname='host1',**opts)
            host2 = s_axon.AxonHost(dir2,hostname='host2',**opts)

            props = {
                'syncmax':s_axon.megabyte,
                'bytemax':s_axon.megabyte,
            }

            axfo0 = host0.add(**props)

            axon0 = s_telepath.openlink( axfo0[1].get('link') )
            self.assertTrue( axon0._waitClonesReady(timeout=2) )

            iden = axon0.alloc(100)
            blob = axon0.chunk(iden,b'V'*100)

            self.assertIsNotNone(blob)

            self.assertTrue( axon0.has( 'md5', blob[1].get('hash:md5') ) )
            self.assertTrue( axon0.has( 'sha1', blob[1].get('hash:sha1') ) )
            self.assertTrue( axon0.has( 'sha256', blob[1].get('hash:sha256') ) )

            axon0.fini()

            host0.fini()
            host1.fini()
            host2.fini()

        dmon.fini()

    def test_axon_clustered(self):

        self.thisHostMustNot(platform='windows')

        busurl = 'local://%s/axons' % guid()

        dmon = s_daemon.Daemon()
        dmon.listen(busurl)

        dmon.share('axons', s_service.SvcBus(), fini=True)

        with self.getTestDir() as datadir:

            dir0 = gendir(datadir,'host0')
            dir1 = gendir(datadir,'host1')
            dir2 = gendir(datadir,'host2')

            opts = {
                'axonbus':busurl,
            }

            host0 = s_axon.AxonHost(dir0,hostname='host0',**opts)
            host1 = s_axon.AxonHost(dir1,hostname='host1',**opts)
            host2 = s_axon.AxonHost(dir2,hostname='host2',**opts)

            props = {
                'clones':2,
                'syncmax':s_axon.megabyte,
                'bytemax':s_axon.megabyte,
            }

            axfo0 = host0.add(**props)

            axon0 = s_telepath.openlink( axfo0[1].get('link') )

            # wait for clones to come online
            self.assertTrue( axon0._waitClonesReady(timeout=2) )

            #self.assertIsNotNone( usage.get('total') )
            #axon = host.axons.get(iden)

            iden = axon0.alloc(100)
            blob = axon0.chunk(iden,b'V'*100)

            self.assertIsNotNone(blob)

            self.assertTrue( axon0.has( 'md5', blob[1].get('hash:md5') ) )
            self.assertTrue( axon0.has( 'sha1', blob[1].get('hash:sha1') ) )
            self.assertTrue( axon0.has( 'sha256', blob[1].get('hash:sha256') ) )

            axon0.fini()

            host0.fini()
            host1.fini()
            host2.fini()

        dmon.fini()

    def test_axon_cluster(self):

        self.thisHostMustNot(platform='windows')

        busurl = 'local://%s/axons' % guid()

        dmon = s_daemon.Daemon()
        dmon.listen(busurl)

        dmon.share('axons', s_service.SvcBus(), fini=True)
        svcprox = s_service.openurl( busurl )

        axcluster = s_axon.AxonCluster(svcprox)

        with self.getTestDir() as datadir:

            dir0 = gendir(datadir,'host0')
            dir1 = gendir(datadir,'host1')
            dir2 = gendir(datadir,'host2')

            opts = {
                'axonbus':busurl,
            }

            host0 = s_axon.AxonHost(dir0,hostname='host0',**opts)
            host1 = s_axon.AxonHost(dir1,hostname='host1',**opts)
            host2 = s_axon.AxonHost(dir2,hostname='host2',**opts)


            props = {
                'clones':1,
                'syncmax':s_axon.megabyte,
                'bytemax':s_axon.megabyte,
            }

            axfo0 = host0.add(**props)

            self.assertFalse( axcluster.has('md5',craphash) )
            self.assertFalse( axcluster.has('md5',asdfhash) )

            buf = b'asdfasdf'
            iden = axcluster.alloc(len(buf))
            self.assertIsNotNone( axcluster.chunk(iden, buf) )

            self.assertFalse( axcluster.has('md5',craphash) )
            self.assertTrue( axcluster.has('md5',asdfhash) )

            blobs = axcluster.find('md5', craphash)
            self.assertEqual(len(blobs), 0)

            blobs = axcluster.find('md5', asdfhash)
            self.assertEqual(len(blobs), 1)

            blob = blobs[0]
            byts = b''.join( axcluster.iterblob(blob) )
            self.assertEqual(byts, buf)

            blob[1].pop('.axon')
            byts = b''.join( axcluster.iterblob(blob) )
            self.assertEqual(byts, buf)

            self.assertIsNone(axcluster.wants('md5', asdfhash, len(buf)))
            self.assertIsNotNone(axcluster.wants('md5', craphash, len(buf)))

            host0.fini()
            host1.fini()
            host2.fini()

        dmon.fini()

    def test_axon_autorun(self):

        self.thisHostMustNot(platform='windows')

        with self.getTestDir() as dirname:

            opts = {
                'autorun':2,
                'syncmax':s_axon.megabyte,
                'bytemax':s_axon.megabyte,
            }
            host = s_axon.AxonHost(dirname,**opts)
            self.assertEqual( len(host.axons), 2 )
            host.fini()

    def test_axon_eatbytes(self):
        self.thisHostMustNot(platform='windows')

        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                blob0 = axon.eatbytes(b'visi')
                with io.BytesIO(b'vertex') as fd:
                    blob1 = axon.eatfd(fd)

                port = axon.getAxonInfo()[1].get('link')[1].get('port')

                with s_axon.openurl('tcp://127.0.0.1/axon', port=port) as prox:
                    blob2 = axon.eatbytes(b'hurr')
                    with io.BytesIO(b'durr') as fd:
                        blob3 = axon.eatfd(fd)

        self.eq( blob0[1].get('axon:blob'), '442f602ecf8230b2a59a44b4f845be27' )
        self.eq( blob1[1].get('axon:blob'), 'd4552906c1f6966b96d27e6fc79441b5' )
        self.eq( blob2[1].get('axon:blob'), '0d60960570ef6da0a15f68c24b420334' )
        self.eq( blob3[1].get('axon:blob'), '97c11d1057f75c9c0b79090131709f62' )

    #def test_axon_proxy(self):

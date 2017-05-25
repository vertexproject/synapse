import io
import hashlib
import tempfile

import synapse.axon as s_axon
import synapse.daemon as s_daemon
import synapse.lib.heap as s_heap
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath
import synapse.lib.service as s_service

from synapse.exc import *
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

                with s_telepath.openurl('tcp://127.0.0.1/axon', port=port) as prox:
                    blob2 = prox.eatbytes(b'hurr')
                    with io.BytesIO(b'durr') as fd:
                        blob3 = prox.eatfd(fd)

        self.eq( blob0[1].get('axon:blob'), '442f602ecf8230b2a59a44b4f845be27' )
        self.eq( blob1[1].get('axon:blob'), 'd4552906c1f6966b96d27e6fc79441b5' )
        self.eq( blob2[1].get('axon:blob'), '0d60960570ef6da0a15f68c24b420334' )
        self.eq( blob3[1].get('axon:blob'), '97c11d1057f75c9c0b79090131709f62' )

    #def test_axon_proxy(self):

    # Axon File System Tests
    def test_axon_fs_create(self):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                axon.fs_create('/foofile', 33204)
                actual = axon.fs_getattr('/foofile')

                self.assertEqual(actual['st_nlink'], 1)
                self.assertEqual(actual['st_mode'], 33204)
                self.assertGreater(actual['st_atime'], 1000000000)
                self.assertGreater(actual['st_ctime'], 1000000000)
                self.assertGreater(actual['st_mtime'], 1000000000)

                self.assertRaises(NoSuchDir, axon.fs_create, '/foodir/foo2', 33204)
                #self.assertRaises(NoSuchDir, axon.fs_create, 'foo2nope', 33204)  # No parent

    def test_axon_fs_getattr(self):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                actual = axon.fs_getattr('/')

                self.assertEqual(actual['st_nlink'], 2)
                self.assertEqual(actual['st_mode'], 16893)
                self.assertGreater(actual['st_atime'], 1000000000)
                self.assertGreater(actual['st_ctime'], 1000000000)
                self.assertGreater(actual['st_mtime'], 1000000000)

    def test_axon_fs_getxattr(self):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                actual = axon.fs_getattr('/')
                self.assertEqual(actual['st_nlink'], 2)
                self.assertEqual(actual['st_mode'], 16893)
                self.assertGreater(actual['st_atime'], 1000000000)
                self.assertGreater(actual['st_ctime'], 1000000000)
                self.assertGreater(actual['st_mtime'], 1000000000)

                nlink = axon.fs_getxattr('/','st_nlink')
                self.assertEqual(nlink, actual['st_nlink'])
                self.assertRaises(NoSuchData, axon.fs_getxattr, '/', 'zzz')
                self.assertRaises(NoSuchData, axon.fs_getxattr, '/haha', 'st_nlink')

    def test_axon_fs_mkdir(self):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                actual = axon.fs_mkdir('/foo', 0x1FD)
                self.assertEqual(actual, None)

                actual = axon.fs_getattr('/foo')
                self.assertEqual(actual['st_nlink'], 2)
                self.assertEqual(actual['st_mode'], 16893)
                self.assertGreater(actual['st_atime'], 1000000000)
                self.assertGreater(actual['st_ctime'], 1000000000)
                self.assertGreater(actual['st_mtime'], 1000000000)

                self.assertRaises(NoSuchDir, axon.fs_mkdir, '/foodir/foo2', 16893)
                #self.assertRaises(NoSuchDir, axon.fs_mkdir, 'noparent', 16893)

                self.assertRaises(FileExists, axon.fs_mkdir, '/foo', 0x1FD)


    def test_axon_fs_read(self, *args, **kwargs):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                data = b'haha\n'

                fd = tempfile.SpooledTemporaryFile()
                fd.write(data)

                axon.fs_create('/haha', 33204)

                _, blobprops = axon.eatfd(fd)
                blobsize = blobprops.get('axon:blob:size')
                blob = blobprops.get('axon:blob')

                axon._fs_update_blob('/haha', blobsize, blob)
                fd.close()

                sz = axon.fs_getattr('/haha').get('st_size')
                actual = axon.fs_read('/haha', sz, 0)
                self.assertEqual(actual, data)

                self.assertRaises(NoSuchEntity, axon.fs_read, '/hoho2', 100, 0)

                axon.fs_create('/haha2', 33204)
                actual = axon.fs_read('/haha2', 1000000000, 0)
                self.assertEqual(actual, b'')

    def test_axon_fs_readdir(self, *args, **kwargs):
        raise unittest.SkipTest('FIXME file path norm breakage')
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                axon.fs_create('/foofile', 33204)
                self.assertEqual(sorted(axon.fs_readdir('/')), sorted(['.', '..', 'foofile']))

                self.assertRaises(NoSuchEntity, axon.fs_readdir, '/haha')
                self.assertRaises(NotSupported, axon.fs_readdir, '/foofile')

    def test_axon_fs_rmdir(self, *args, **kwargs):
        raise unittest.SkipTest('FIXME file path norm breakage')
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                axon.fs_mkdir('/foo', 0x1FD)
                axon.fs_create('/foo/haha', 33204)

                self.assertRaises(NotEmpty, axon.fs_rmdir, '/foo')

                axon.fs_unlink('/foo/haha')
                self.nn(axon.fs_getattr('/foo'))
                axon.fs_rmdir('/foo')
                self.assertRaises(NoSuchEntity, axon.fs_getattr, '/foo')
                self.assertRaises(NoSuchEntity, axon.fs_rmdir, '/foo')

    def test_axon_fs_rename(self, *args, **kwargs):
        raise unittest.SkipTest('FIXME file path norm breakage')
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                axon.fs_mkdir('/dir', 0x1FD)
                axon.fs_create('/dir/a', 33204)
                axon.fs_rename('/dir/a', '/dir/b')

                actual = axon.fs_readdir('/dir')
                self.assertEqual(sorted(actual), ['.','..','b'])

                # source doesnt exist
                self.assertRaises(NoSuchEntity, axon.fs_rename, 'fake', 'other')

                # source doesnt have parent
                tufo = axon.core.getTufoByProp('axon:path', '/dir')
                axon.core.delTufo(tufo)
                self.assertRaises(NoSuchDir, axon.fs_rename, '/dir/b', '/dir/c')

                # dst doesnt have parent
                axon.fs_mkdir('/dira', 0x1FD)
                axon.fs_mkdir('/dirb', 0x1FD)
                axon.fs_create('/dira/a', 33204)
                tufo = axon.core.getTufoByProp('axon:path', '/dirb')
                axon.core.delTufo(tufo)
                self.assertRaises(NoSuchDir, axon.fs_rename, '/dira/a', '/dirb/b')

                # dst not empty
                axon.fs_mkdir('/flda', 0x1FD)
                axon.fs_mkdir('/fldb', 0x1FD)
                axon.fs_create('/flda/a', 33204)
                axon.fs_create('/fldb/a', 33204)
                self.assertRaises(NotEmpty, axon.fs_rename, '/flda', '/fldb')

                # overwrite a regular file with a directory
                axon.fs_mkdir('/adir', 0x1FD)
                axon.fs_create('/reg', 33204)
                axon.fs_rename('/adir', '/reg')
                self.none(axon.fs_getattr('/reg').get('st_size'))

                # update all the kids
                axon.fs_mkdir('/cool', 0x1FD)
                axon.fs_create('/cool/a', 33204)
                axon.fs_create('/cool/b', 33204)
                axon.fs_create('/cool/c', 33204)
                axon.fs_rename('/cool', '/cooler')

                self.assertRaises(NoSuchEntity, axon.fs_getattr, '/cool')
                self.assertRaises(NoSuchEntity, axon.fs_getattr, '/cool/a')
                self.assertRaises(NoSuchEntity, axon.fs_getattr, '/cool/b')
                self.assertRaises(NoSuchEntity, axon.fs_getattr, '/cool/c')

                self.nn(axon.fs_getattr('/cooler'))
                self.nn(axon.fs_getattr('/cooler/a'))
                self.nn(axon.fs_getattr('/cooler/b'))
                self.nn(axon.fs_getattr('/cooler/c'))

                # nested dirs
                axon.fs_mkdir('/nest1', 0x1FD)
                axon.fs_mkdir('/nest1/nest2', 0x1FD)
                axon.fs_mkdir('/nest1/nest2/nest3', 0x1FD)
                axon.fs_create('/nest1/nest2/nest3/reg', 33204)

                axon.fs_rename('/nest1', '/nest')

                self.nn(axon.fs_getattr('/nest'))
                self.nn(axon.fs_getattr('/nest/nest2'))
                self.nn(axon.fs_getattr('/nest/nest2/nest3'))
                self.nn(axon.fs_getattr('/nest/nest2/nest3/reg'))


    def test_axon_fs_truncate(self, *args, **kwargs):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                axon.fs_create('/foofile', 33204)
                tufo = axon.core.getTufoByProp('axon:path','/foofile')
                axon.core.setTufoProps(tufo, st_size=100, blob=32*'a')
                self.assertEqual(tufo[1].get('axon:path:st_size'), 100)
                self.assertEqual(tufo[1].get('axon:path:blob'), 32*'a')

                axon.fs_truncate('/foofile')
                tufo = axon.core.getTufoByProp('axon:path','/foofile')
                self.assertEqual(tufo[1].get('axon:path:st_size'), 0)
                self.assertEqual(tufo[1].get('axon:path:blob'), None)

                axon.fs_truncate('/notthere')  # FIXME - should this raise exception?

    def test_axon_fs_unlink(self, *args, **kwargs):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                axon.fs_create('/foofile', 33204)

                actual = axon.fs_getattr('/foofile')
                self.assertEqual(actual['st_nlink'], 1)
                self.assertEqual(actual['st_mode'], 33204)
                self.assertGreater(actual['st_atime'], 1000000000)
                self.assertGreater(actual['st_ctime'], 1000000000)
                self.assertGreater(actual['st_mtime'], 1000000000)

                axon.fs_unlink('/foofile')
                self.assertRaises(NoSuchEntity, axon.fs_getattr, '/foofile')
                self.assertRaises(NoSuchFile, axon.fs_unlink, '/foofile')

    def test_axon_fs_utimens(self, *args, **kwargs):
        with self.getTestDir() as dirname:
            with s_axon.Axon(dirname) as axon:

                axon.fs_create('/foofile', 33204)
                actual = axon.fs_getattr('/foofile')
                ctime = actual['st_ctime']

                self.assertGreater(actual['st_atime'], 1000000000)
                self.assertGreater(actual['st_ctime'], 1000000000)
                self.assertGreater(actual['st_mtime'], 1000000000)

                axon.fs_utimens('/foofile', (0, 0))
                actual = axon.fs_getattr('/foofile')

                self.assertEqual(actual['st_mtime'], 0)
                self.assertEqual(actual['st_ctime'], ctime)
                self.assertEqual(actual['st_atime'], 0)

                axon.fs_utimens('/foofile')
                self.assertEqual(actual['st_mtime'], 0)
                self.assertEqual(actual['st_ctime'], ctime)
                self.assertEqual(actual['st_atime'], 0)

    # test_axon_fs_write  - do not implement this function

    def test_axon__fs_isdir(self, *args, **kwargs):
        self.assertEqual(s_axon.Axon._fs_isdir(None), False)
        self.assertEqual(s_axon.Axon._fs_isdir(0), False)
        self.assertEqual(s_axon.Axon._fs_isdir(33204), False)
        self.assertEqual(s_axon.Axon._fs_isdir(16893), True)

    def test_axon__fs_isfile(self, *args, **kwargs):
        self.assertEqual(s_axon.Axon._fs_isfile(None), False)
        self.assertEqual(s_axon.Axon._fs_isfile(0), False)
        self.assertEqual(s_axon.Axon._fs_isfile(33204), True)
        self.assertEqual(s_axon.Axon._fs_isfile(16893), False)

    def test_axon_get_renameprops(self, *args, **kwargs):
        tufo = ('99ac9490ad2e1d4669de1c005a4ec666',
            {'tufo:form': 'axon:path', 'axon:path:st_ctime': 1491191818, 'axon:path:st_mode': 16893, 'axon:path:parent': '/',
            'axon:path:st_atime': 1491191818, 'axon:path': '/dir', 'axon:path:base': 'dir', 'axon:path:dir': '/',
            'axon:path:st_nlink': 3, 'axon:path:st_mtime': 1491191818, 'axon:path:blob': 32 * 'a'})
        actual = s_axon.Axon._get_renameprops(tufo)

        self.assertEqual(actual['st_nlink'], 3)
        self.assertEqual(actual['st_mode'], 16893)
        self.assertEqual(actual['blob'], 32 * 'a')
        self.assertGreater(actual['st_atime'], 1000000000)
        self.assertGreater(actual['st_ctime'], 1000000000)
        self.assertGreater(actual['st_mtime'], 1000000000)

    def test_axon_telepath(self):
        with self.getTestDir() as dirname:

            with s_daemon.Daemon() as dmon:

                link = dmon.listen('tcp://127.0.0.1:0/')
                port = link[1].get('port')

                with s_axon.Axon(dirname) as axon:
                    dmon.share('axon',axon)

                    prox = s_telepath.openurl('tcp://127.0.0.1/axon', port=port)

                    with io.BytesIO(b'vertex') as fd:
                        blob = prox.eatfd(fd)
                        print(blob)

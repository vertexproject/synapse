
import shutil
import tarfile
import zipfile
import tempfile

from synapse.tests.common import *

import synapse.exc as s_exc
import synapse.lib.filepath as s_filepath

class TestFilePath(SynTest):

    def test_filepath_objects(self):
        temp_dir = tempfile.mkdtemp()
        name = temp_dir

        # FilePath base object defaults
        fp = s_filepath.FilePath(name, parent=None, fd=None)
        self.assertIsNone(fp.open())
        self.assertTrue(fp.isfile())
        self.assertIsNone(fp.parent())
        self.eq(temp_dir, fp.path())

        # CntrPathDir
        path = getTestPath('nest2.tar')
        tar = s_filepath.FpTar(path)
        cpd = s_filepath.CntrPathDir('foo', parent=tar)
        self.assertFalse(cpd.isfile())
        self.assertIsNone(cpd.open())

        # FpTarFile
        path = getTestPath('nest2.tar')
        tar = s_filepath.FpTar(path)
        ftf = s_filepath.FpTarFile('nnfoo', parent=tar)
        self.assertTrue(ftf.isfile())

        shutil.rmtree(temp_dir)

    def test_filepath_regular(self):
        temp_fd = tempfile.NamedTemporaryFile()
        temp_dir = tempfile.mkdtemp()

        fbuf = b'A'*20
        temp_fd.write(fbuf)
        temp_fd.flush()

        # file and dir that exist
        self.assertTrue(s_filepath.exists(temp_fd.name))
        self.assertTrue(s_filepath.exists(temp_dir))
        self.assertTrue(s_filepath.exists('/'))

        # DNE in a real directory
        path = os.path.join(temp_dir, 'dne')
        self.assertFalse(s_filepath.exists(path))

        # open regular file
        fd = s_filepath.openFile(temp_fd.name, mode='rb')
        self.assertEqual(fd.read(), fbuf)

        # dne path
        self.assertRaises(s_exc.NoSuchPath, s_filepath.openFile, '%s%s' % (temp_fd.name, '_DNE'), mode='rb')
        self.assertRaises(s_exc.NoSuchPath, s_filepath.openFile, None)
        self.assertRaises(s_exc.NoSuchPath, s_filepath.openFile, '')

        # open a directory 
        self.assertIsNone(s_filepath.openFile('/tmp', mode='rb', req=False))
        self.assertIsNone(s_filepath.openFile('/', req=False))

        temp_fd.close()
        os.rmdir(temp_dir)

    def test_filepath_zip(self):
        temp_fd = tempfile.NamedTemporaryFile()
        nested_temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        zip_fd.writestr('foo', 'A'*20)
        zip_fd.writestr('dir0/bar', 'A'*20)
        zip_fd.writestr('dir0/dir1/dir2/baz', 'C'*20)

        zip_fd.close()

        zip_fd = zipfile.ZipFile(nested_temp_fd.name, 'w')
        zip_fd.writestr('aaa', 'A'*20)
        zip_fd.writestr('ndir0/bbb', 'A'*20)
        zip_fd.writestr('ndir0/ndir1/ndir2/ccc', 'C'*20)
        zip_fd.write(temp_fd.name, arcname='ndir0/nested.zip')

        zip_fd.close()

        # container is path
        path = nested_temp_fd.name
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # base directory that exists
        path = os.path.join(temp_fd.name, 'dir0')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isdir(path))

        # container nested dir that exists
        path = os.path.join(nested_temp_fd.name, 'ndir0', 'nested.zip', 'dir0')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isdir(path))

        # container nested file that exists
        path = os.path.join(nested_temp_fd.name, 'ndir0', 'nested.zip', 'dir0', 'bar')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # container nested DNE path
        path = os.path.join(nested_temp_fd.name, 'ndir0', 'nested.zip', 'dir0', 'dne')
        self.assertFalse(s_filepath.exists(path))
        self.assertFalse(s_filepath.isfile(path))
        self.assertFalse(s_filepath.isdir(path))

        # base file that exists
        path = os.path.join(temp_fd.name, 'foo')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'bar')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # nested dir that exists
        path = os.path.join(temp_fd.name, 'dir0', 'dir1', 'dir2')
        self.assertTrue(s_filepath.isdir(path))

        # DNE in a real directory
        path = os.path.join(temp_fd.name, 'dir0', 'dne')
        self.assertFalse(s_filepath.exists(path))
        self.assertFalse(s_filepath.isfile(path))
        self.assertFalse(s_filepath.isdir(path))

        # DNE base
        path = os.path.join(temp_fd.name, 'dne')
        self.assertFalse(s_filepath.exists(path))
        self.assertFalse(s_filepath.isfile(path))
        self.assertFalse(s_filepath.isdir(path))

        temp_fd.close()

    def test_filepath_zip_open(self):
        temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        abuf = 'A'*20
        bbuf = b'A'*20
        zip_fd.writestr('dir0/foo', abuf)
        fbuf2 = 'B'*20
        zip_fd.writestr('bar', fbuf2)

        zip_fd.close()

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        self.assertTrue(s_filepath.isfile(path))

        # open zip file
        path = temp_fd.name
        fd0 = s_filepath.openFile(path, mode='rb')
        fd1 = open(path, mode='rb')
        self.assertEqual(fd0.read(), fd1.read())

        # open inner zip file
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        fd = s_filepath.openFile(path, mode='r')
        self.assertEqual(fd.read(), bbuf)

        temp_fd.close()

    def test_filepath_tar(self):
        
        # container is path
        path = getTestPath('nest2.tar')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # base directory that exists
        path = getTestPath('nest2.tar', 'nndir0')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isdir(path))

        # file that exists in a tar
        path = getTestPath('nest2.tar', 'nndir0', 'nnbar')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # container nested base directory that exists
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'ndir0')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isdir(path))

        # container nested file that exists
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'nfoo')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # container nested file that exists
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'ndir0', 'ndir1', 'nest0.zip', 'foo')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # container nested path that DNE
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'ndir0', 'dne')
        self.assertFalse(s_filepath.exists(path))
        self.assertFalse(s_filepath.isdir(path))
        self.assertFalse(s_filepath.isfile(path))

        # DNE file in a real directory
        path = getTestPath('nest2.tar', 'nndir0', 'dne')
        self.assertFalse(s_filepath.exists(path))
        self.assertFalse(s_filepath.isfile(path))
        self.assertFalse(s_filepath.isdir(path))

        # DNE base
        path = getTestPath('nest2.tar', 'dne')
        self.assertFalse(s_filepath.exists(path))
        self.assertFalse(s_filepath.isfile(path))
        self.assertFalse(s_filepath.isdir(path))

    def test_filepath_tar_open(self):

        # open tar file
        path = getTestPath('nest2.tar')
        fd = s_filepath.openFile(path, mode='rb')
        fs_fd = open(getTestPath('nest2.tar'), 'rb')
        self.assertEqual(fd.read(), fs_fd.read())

        # open inner tar file
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar')
        fd = s_filepath.openFile(path, mode='rb')
        fs_fd = open(getTestPath('nest1.tar'), 'rb')
        self.assertEqual(fd.read(), fs_fd.read())

        # open inner file
        path = getTestPath('nest2.tar', 'nnfoo')
        fd = s_filepath.openFile(path, mode='rb')
        buf = b'A'*20
        buf += b'\n'
        self.assertEqual(fd.read(), buf)


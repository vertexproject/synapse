
import shutil
import tarfile
import zipfile
import tempfile

from synapse.tests.common import *

import synapse.lib.filepath as s_filepath

class TestFilePath(SynTest):

    def test_filepath_regular(self):
        temp_fd = tempfile.NamedTemporaryFile()
        temp_dir = tempfile.mkdtemp()

        fbuf = b'A'*20
        temp_fd.write(fbuf)
        temp_fd.flush()

        # file and dir that exist
        self.assertTrue(s_filepath.exists(temp_fd.name))
        self.assertTrue(s_filepath.exists(temp_dir))

        # DNE in a real directory
        path = os.path.join(temp_dir, 'dne')
        self.assertFalse(s_filepath.exists(path))

        # open regular file
        fd = s_filepath._open(temp_fd.name, mode='rb')
        self.assertEqual(fd.read(), fbuf)

        temp_fd.close()
        os.rmdir(temp_dir)

    def test_filepath_zip_exists(self):
        temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        zip_fd.writestr('dir0/foo', 'A'*20)
        zip_fd.writestr('bar', 'B'*20)

        zip_fd.close()

        # base directory that exists
        path = os.path.join(temp_fd.name, 'dir0')
        self.assertTrue(s_filepath.exists(path))

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        self.assertTrue(s_filepath.exists(path))

        # DNE file in a real directory
        path = os.path.join(temp_fd.name, 'dir0', 'dne')
        self.assertFalse(s_filepath.exists(path))

        # DNE base
        path = os.path.join(temp_fd.name, 'dne')
        self.assertFalse(s_filepath.exists(path))

        temp_fd.close()

    def test_filepath_zip_isfile(self):
        temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        zip_fd.writestr('dir0/foo', 'A'*20)
        zip_fd.writestr('bar', 'B'*20)

        zip_fd.close()

        # base file that exists
        path = os.path.join(temp_fd.name, 'bar')
        self.assertTrue(s_filepath.isfile(path))

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        self.assertTrue(s_filepath.isfile(path))

        # DNE file in a real directory
        path = os.path.join(temp_fd.name, 'dir0', 'dne')
        self.assertFalse(s_filepath.isfile(path))

        # DNE base file
        path = os.path.join(temp_fd.name, 'dne')
        self.assertFalse(s_filepath.isfile(path))

        temp_fd.close()

    def test_filepath_zip_isdir(self):
        temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        zip_fd.writestr('foo', 'A'*20)
        zip_fd.writestr('dir0/bar', 'B'*20)
        zip_fd.writestr('dir0/dir1/dir2/baz', 'C'*20)

        zip_fd.close()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'r')

        # base dir that exists
        path = os.path.join(temp_fd.name, 'dir0')
        self.assertTrue(s_filepath.isdir(path))

        # nested dir that exists
        path = os.path.join(temp_fd.name, 'dir0', 'dir1', 'dir2')
        self.assertTrue(s_filepath.isdir(path))

        # DNE nested dir
        path = os.path.join(temp_fd.name, 'dir0', 'dne')
        self.assertFalse(s_filepath.isdir(path))

        temp_fd.close()

    def test_filepath_zip_open(self):
        temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        fbuf = 'A'*20
        bbuf = b'A'*20
        zip_fd.writestr('dir0/foo', fbuf)
        fbuf2 = 'B'*20
        zip_fd.writestr('bar', fbuf2)

        zip_fd.close()

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        self.assertTrue(s_filepath.isfile(path))

        # open zip file
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        fd = s_filepath._open(path, mode='r')
        self.assertEqual(fd.read(), bbuf)

        temp_fd.close()

    def test_filepath_tar(self):
        temp_fd = tempfile.NamedTemporaryFile()
        temp_d = tempfile.mkdtemp()

        os.mkdir(os.path.join(temp_d, 'dir0'))

        with open(os.path.join(temp_d, 'dir0', 'foo'), 'w') as fd:
            fd.write('A'*20)
        with open(os.path.join(temp_d, 'bar'), 'w') as fd:
            fd.write('B'*20)
        
        fd = tarfile.TarFile(temp_fd.name, mode='w')
        #fd.writestr('dir0/foo', 'A'*20)
        #fd.writestr('bar', 'B'*20)
        fd.add(os.path.join(temp_d, 'dir0'), arcname='dir0')
        fd.add(os.path.join(temp_d, 'bar'), arcname='bar')
        fd.close()

        # base directory that exists
        path = os.path.join(temp_fd.name, 'dir0')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isdir(path))

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        self.assertTrue(s_filepath.exists(path))
        self.assertTrue(s_filepath.isfile(path))

        # DNE file in a real directory
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
        shutil.rmtree(temp_d)

    def test_filepath_tar_open(self):
        temp_fd = tempfile.NamedTemporaryFile()
        temp_d = tempfile.mkdtemp()

        os.mkdir(os.path.join(temp_d, 'dir0'))
        bbuf = b'A'*20
        with open(os.path.join(temp_d, 'dir0', 'foo'), 'w') as fd:
            fd.write('A'*20)
        with open(os.path.join(temp_d, 'bar'), 'w') as fd:
            fd.write('B'*20)
        
        fd = tarfile.TarFile(temp_fd.name, mode='w')
        fd.add(os.path.join(temp_d, 'dir0'), arcname='dir0')
        fd.add(os.path.join(temp_d, 'bar'), arcname='bar')

        fd.close()

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        self.assertTrue(s_filepath.isfile(path))

        # open tar file
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        fd = s_filepath._open(path, mode='r')
        self.assertEqual(fd.read(), bbuf)

        temp_fd.close()
        shutil.rmtree(temp_d)


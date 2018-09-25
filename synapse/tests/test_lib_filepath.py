import os
import io
import shutil
import tarfile
import zipfile
import tempfile

from synapse.tests.common import getTestPath
import synapse.tests.utils as s_t_utils

import synapse.exc as s_exc
import synapse.lib.filepath as s_filepath

class TestFilePath(s_t_utils.SynTest):

    def test_filepath_glob(self):
        temp_dir = tempfile.mkdtemp()

        os.mkdir(os.path.join(temp_dir, 'dir0'))
        os.mkdir(os.path.join(temp_dir, 'dir1'))
        os.mkdir(os.path.join(temp_dir, 'dir2'))
        os.mkdir(os.path.join(temp_dir, 'fooD'))
        os.makedirs(os.path.join(temp_dir, 'bazer', 'eir0', 'dir1'))
        os.makedirs(os.path.join(temp_dir, 'bazer', 'eir0', 'dir2'))

        f0 = b'A' * 20
        f0_path = os.path.join(temp_dir, 'foo0')
        with open(f0_path, 'wb') as fd:
            fd.write(f0)

        f1 = b'B' * 20
        f1_path = os.path.join(temp_dir, 'foo1')
        with open(f1_path, 'wb') as fd:
            fd.write(f1)

        f2 = b'C' * 20
        f2_path = os.path.join(temp_dir, 'foo2')
        with open(f2_path, 'wb') as fd:
            fd.write(f2)

        f3 = b'Z' * 20
        f3_path = os.path.join(temp_dir, 'junk')
        with open(f3_path, 'wb') as fd:
            fd.write(f3)

        # same files alpha/bravo
        t1 = b'a' * 20
        t_path = os.path.join(temp_dir, 'bazer', 'eir0', 'dir1', 'alpha')
        with open(t_path, 'wb') as fd:
            fd.write(t1)

        t_path = os.path.join(temp_dir, 'bazer', 'eir0', 'dir1', 'bravo')
        with open(t_path, 'wb') as fd:
            fd.write(t1)

        t_path = os.path.join(temp_dir, 'bazr')
        with open(t_path, 'wb') as fd:
            fd.write(t1)

        # files that exists
        path = os.path.join(temp_dir, 'foo*')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isfile(path))
        self.false(s_filepath.isdir(path))

        # dirs that exist
        path = os.path.join(temp_dir, 'dir*')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isfile(path))
        self.false(s_filepath.isdir(path))
        # open a dir
        fp = s_filepath.parsePath(temp_dir, 'dir0')
        self.none(fp.open())

        # multiple open regular files
        path = os.path.join(temp_dir, 'foo*')
        fd_ct = 0
        f = [fd for fd in s_filepath.openfiles(path, mode='rb', req=False)]
        for fd in f:
            buf = fd.read()
            self.eq(len(buf), 20)
            self.isin(buf, [f0, f1, f2])
            fd.close()
            fd_ct += 1
        self.eq(fd_ct, 3)

        # multiple open on dir
        path = os.path.join(temp_dir, 'dir*')
        def diropen(path):
            [f for f in s_filepath.openfiles(path, mode='rb', req=True)]
        self.raises(s_exc.NoSuchPath, diropen, path)

        path = os.path.join(temp_dir, 'dir*')
        def diropen(path):
            return [f for f in s_filepath.openfiles(path, mode='rb', req=False)]
        self.eq([], diropen(path))

        # multiple open on dne
        path = os.path.join(temp_dir, 'dne*')
        def diropen(path):
            return [f for f in s_filepath.openfiles(path, mode='rb', req=True)]
        self.raises(s_exc.NoSuchPath, diropen, path)

        ret = [a for a in s_filepath.openfiles(None)]
        self.eq([], ret)

        # multiple open zip files
        tzfd0 = open(os.path.join(temp_dir, 'baz.zip'), 'w')
        tzfd1 = tempfile.NamedTemporaryFile()
        ttfd0 = open(os.path.join(temp_dir, 'baz.tar'), 'w')

        zfd0 = zipfile.ZipFile(tzfd0.name, 'w')
        zfd0.writestr('dir0/dir1/dir2/foo0', f0)
        zfd0.writestr('dir0/dir1/dir2/foo1', f1)
        zfd0.writestr('dir0/dir1/dir2/foo2', f2)
        zfd0.writestr('dir0/dir1/dir2/junk', 'Z' * 20)
        zfd0.writestr('eir0/dir3/z1', t1)
        zfd0.writestr('eir0/dir4/z2', t1)
        zfd0.close()

        tfd0 = tarfile.TarFile(ttfd0.name, 'w')
        tfd0.add(f0_path, arcname='dir0/dir1/dir2/foo0')
        tfd0.add(f1_path, arcname='dir0/dir1/dir2/foo1')
        tfd0.add(f2_path, arcname='dir0/dir1/dir2/foo2')
        tfd0.add(f3_path, arcname='dir0/dir1/dir2/junk')
        tfd0.add(t_path, arcname='eir0/dir5/t1')
        tfd0.add(t_path, arcname='eir0/dir6/t2')
        tfd0.close()

        zfd1 = zipfile.ZipFile(tzfd1.name, 'w')
        zfd1.writestr('dir0/dir1/dir2/bar0', f0)
        zfd1.writestr('dir0/dir1/dir2/bar1', f1)
        zfd1.writestr('dir0/dir1/dir2/bar2', f2)
        zfd1.writestr('dir0/dir1/dir2/junk', 'Z' * 20)
        zfd1.write(tzfd0.name, arcname='ndir0/nested.zip')
        zfd1.write(ttfd0.name, arcname='ndir0/nested.tar')
        zfd1.close()

        path = os.path.join(tzfd1.name, 'dir0/dir1/dir2/bar*')
        count = 0
        for fd in s_filepath.openfiles(path, mode='rb'):
            buf = fd.read()
            fd.seek(0)
            self.eq(len(buf), 20)
            self.eq(buf, fd.read())
            self.isin(buf, [f0, f1, f2])
            fd.close()
            count += 1
        self.eq(count, 3)

        path = os.path.join(temp_dir, 'baz*', 'eir0', 'dir*', '*')
        count = 0
        for fd in s_filepath.openfiles(path, mode='rb'):
            buf = fd.read()
            self.eq(len(buf), 20)
            self.eq(buf, t1)
            fd.close()
            count += 1
        self.eq(count, 6)

        tzfd0.close()
        tzfd1.close()
        ttfd0.close()

        shutil.rmtree(temp_dir)

    def test_filepath_regular(self):
        temp_fd = tempfile.NamedTemporaryFile()
        temp_dir = tempfile.mkdtemp()

        fbuf = b'A' * 20
        temp_fd.write(fbuf)
        temp_fd.flush()

        # file and dir that exist
        self.true(s_filepath.exists(temp_fd.name))
        self.true(s_filepath.exists(temp_dir))
        self.true(s_filepath.exists('/'))
        self.false(s_filepath.isfile(temp_dir))
        self.false(s_filepath.isdir(temp_fd.name))

        # DNE in a real directory
        path = os.path.join(temp_dir, 'dne')
        self.false(s_filepath.exists(path))
        self.raises(s_exc.NoSuchPath, s_filepath._pathClass, path)

        # open regular file
        fd = s_filepath.openfile(temp_fd.name, mode='rb')
        self.eq(fd.read(), fbuf)
        fd.close()

        # dne path
        self.raises(s_exc.NoSuchPath, s_filepath.openfile, '%s%s' % (temp_fd.name, '_DNE'), mode='rb')
        self.raises(s_exc.NoSuchPath, s_filepath.openfile, None)
        self.raises(s_exc.NoSuchPath, s_filepath.openfile, '')
        self.none(s_filepath.openfile(None, req=False))

        # open a directory
        self.none(s_filepath.openfile('/tmp', mode='rb', req=False))
        self.none(s_filepath.openfile('/', req=False))

        temp_fd.close()
        shutil.rmtree(temp_dir)

    def test_filepath_zip(self):
        temp_fd = tempfile.NamedTemporaryFile()
        nested_temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        zip_fd.writestr('foo', 'A' * 20)
        zip_fd.writestr('dir0/bar', 'A' * 20)
        zip_fd.writestr('dir0/dir1/dir2/baz', 'C' * 20)

        zip_fd.close()

        zip_fd = zipfile.ZipFile(nested_temp_fd.name, 'w')
        zip_fd.writestr('aaa', 'A' * 20)
        zip_fd.writestr('ndir0/bbb', 'A' * 20)
        zip_fd.writestr('ndir0/ndir1/ndir2/ccc', 'C' * 20)
        zip_fd.write(temp_fd.name, arcname='ndir0/nested.zip')

        zip_fd.close()

        # container is path
        path = nested_temp_fd.name
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # base directory that exists
        path = os.path.join(temp_fd.name, 'dir0')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isdir(path))

        # container nested dir that exists
        path = os.path.join(nested_temp_fd.name, 'ndir0', 'nested.zip', 'dir0')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isdir(path))

        # container nested file that exists
        path = os.path.join(nested_temp_fd.name, 'ndir0', 'nested.zip', 'dir0', 'bar')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # container nested DNE path
        path = os.path.join(nested_temp_fd.name, 'ndir0', 'nested.zip', 'dir0', 'dne')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isfile(path))
        self.false(s_filepath.isdir(path))

        # base file that exists
        path = os.path.join(temp_fd.name, 'foo')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'bar')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # nested dir that exists
        path = os.path.join(temp_fd.name, 'dir0', 'dir1', 'dir2')
        self.true(s_filepath.isdir(path))

        # DNE in a real directory
        path = os.path.join(temp_fd.name, 'dir0', 'dne')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isfile(path))
        self.false(s_filepath.isdir(path))

        # DNE base
        path = os.path.join(temp_fd.name, 'dne')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isfile(path))
        self.false(s_filepath.isdir(path))

        temp_fd.close()
        nested_temp_fd.close()

    def test_filepath_zip_open(self):
        temp_fd = tempfile.NamedTemporaryFile()

        zip_fd = zipfile.ZipFile(temp_fd.name, 'w')
        abuf = 'A' * 20
        bbuf = b'A' * 20
        zip_fd.writestr('dir0/foo', abuf)
        fbuf2 = 'B' * 20
        zip_fd.writestr('bar', fbuf2)

        zip_fd.close()

        # file that exists in a directory
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        self.true(s_filepath.isfile(path))

        # open zip file
        path = temp_fd.name
        fd0 = s_filepath.openfile(path, mode='rb')
        fd1 = open(path, mode='rb')
        self.eq(fd0.read(), fd1.read())
        fd0.close()
        fd1.close()

        # open inner zip file
        path = os.path.join(temp_fd.name, 'dir0', 'foo')
        fd = s_filepath.openfile(path, mode='r')
        self.eq(fd.read(), bbuf)
        fd.close()

        temp_fd.close()
        temp_fd.close()

    def test_filepath_tar(self):

        # container is path
        path = getTestPath('nest2.tar')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # base directory that exists
        path = getTestPath('nest2.tar', 'nndir0')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isdir(path))

        # file that exists in a tar
        path = getTestPath('nest2.tar', 'nndir0', 'nnbar')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # container nested base directory that exists
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'ndir0')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isdir(path))

        # container nested file that exists
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'nfoo')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # container nested file that exists
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'ndir0', 'ndir1', 'nest0.zip', 'foo')
        self.true(s_filepath.exists(path))
        self.true(s_filepath.isfile(path))

        # container nested path that DNE
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar', 'ndir0', 'dne')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isdir(path))
        self.false(s_filepath.isfile(path))

        # DNE file in a real directory
        path = getTestPath('nest2.tar', 'nndir0', 'dne')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isfile(path))
        self.false(s_filepath.isdir(path))

        # DNE base
        path = getTestPath('nest2.tar', 'dne')
        self.false(s_filepath.exists(path))
        self.false(s_filepath.isfile(path))
        self.false(s_filepath.isdir(path))

    def test_filepath_tar_open(self):

        # open tar file
        path = getTestPath('nest2.tar')
        fd = s_filepath.openfile(path, mode='rb')
        fs_fd = open(getTestPath('nest2.tar'), 'rb')
        self.eq(fd.read(), fs_fd.read())
        fs_fd.close()
        fd.close()

        # open inner tar file
        path = getTestPath('nest2.tar', 'nndir0', 'nndir1', 'nest1.tar')
        fd = s_filepath.openfile(path, mode='rb')
        fs_fd = open(getTestPath('nest1.tar'), 'rb')
        self.eq(fd.read(), fs_fd.read())
        fs_fd.close()
        fd.close()

        # open inner file
        path = getTestPath('nest2.tar', 'nnfoo')
        fd = s_filepath.openfile(path, mode='rb')
        buf = b'A' * 20
        buf += b'\n'
        self.eq(fd.read(), buf)
        fd.close()

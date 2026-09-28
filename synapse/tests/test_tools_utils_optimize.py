import os
import shutil
import py_compile
import importlib.util

from unittest import mock

import synapse.common as s_common

import synapse.lib.parser as s_parser

import synapse.tests.utils as s_t_utils
import synapse.tools.utils.optimize as s_optimize

class OptimizeTest(s_t_utils.SynTest):

    async def test_tools_utils_optimize(self):

        # install directories nested inside another one are compiled with it
        paths = {'stdlib': '/opt/py/lib', 'platstdlib': '/opt/py/lib', 'purelib': '/opt/py/lib/site-packages',
                 'platlib': '/opt/py/libx'}
        with mock.patch('sysconfig.get_path', side_effect=paths.get):
            self.eq(['/opt/py/lib', '/opt/py/libx'], s_optimize.getInstallDirs())

        self.len(len(set(s_optimize.getInstallDirs())), s_optimize.getInstallDirs())

        with self.getTestDir() as dirn:

            pkgdir = s_common.gendir(dirn, 'pkg')
            goodpath = os.path.join(pkgdir, 'good.py')
            py2path = os.path.join(pkgdir, 'py2.py')

            with open(goodpath, 'w') as fd:
                fd.write('valu = 10\n')

            with open(py2path, 'w') as fd:
                fd.write('valu = 0xFFFFFFFAL\n')

            with open(os.path.join(pkgdir, 'data.txt'), 'w') as fd:
                fd.write('not python\n')

            def pycs(path):
                return [os.path.isfile(importlib.util.cache_from_source(path, optimization=opt)) for opt in ('', 1)]

            with mock.patch.object(s_optimize, 'getInstallDirs', return_value=[]), \
                 mock.patch.object(s_parser, 'larkcached', True):

                # --check names the importable files which lack bytecode
                outp = self.getTestOutp()
                self.eq(1, await s_optimize.main(['--check', dirn], outp=outp))
                outp.expect('ERROR: 1 importable files lack current bytecode')
                outp.expect(f'{goodpath} (optimization level 0)')
                outp.expect(f'{goodpath} (optimization level 1)')
                self.notin('py2.py', str(outp))
                outp.expect('The Storm grammar parser loads from')

                # a file which does not compile is skipped
                outp = self.getTestOutp()
                with mock.patch.object(s_parser, 'saveLarkParser') as save:
                    self.eq(0, await s_optimize.main([dirn], outp=outp))

                self.eq(1, save.call_count)
                outp.expect('Compiling bytecode at optimization levels [0, 1]')
                outp.expect('Some files did not compile and were skipped.')
                outp.expect('Saved the Storm grammar parser cache')
                self.eq([True, True], pycs(goodpath))
                self.eq([False, False], pycs(py2path))

                outp = self.getTestOutp()
                self.eq(0, await s_optimize.main(['--check', dirn], outp=outp))
                outp.expect('Bytecode is current at optimization levels [0, 1]')

                # the grammar parser must load from its cache
                with mock.patch.object(s_parser, 'larkcached', False):
                    outp = self.getTestOutp()
                    self.eq(1, await s_optimize.main(['--check', dirn], outp=outp))
                    outp.expect('Bytecode is current')
                    outp.expect('ERROR: The Storm grammar parser does not load from')

                # an edited source has stale bytecode
                with open(goodpath, 'w') as fd:
                    fd.write('valu = 1000\n')

                outp = self.getTestOutp()
                self.eq(1, await s_optimize.main(['--check', '--level', '1', dirn], outp=outp))
                outp.expect(f'{goodpath} (optimization level 1)')

                shutil.rmtree(os.path.join(pkgdir, '__pycache__'))
                os.unlink(py2path)

                outp = self.getTestOutp()
                with mock.patch.object(s_parser, 'saveLarkParser') as save:
                    self.eq(0, await s_optimize.main(['--level', '0', dirn], outp=outp))

                self.eq(1, save.call_count)
                outp.expect('Compiling bytecode at optimization levels [0]')
                self.notin('did not compile', str(outp))
                self.eq([True, False], pycs(goodpath))

                # any other compileall failure is fatal
                outp = self.getTestOutp()
                with mock.patch.object(s_optimize, 'compileDirs', return_value=2):
                    with mock.patch.object(s_parser, 'saveLarkParser') as save:
                        self.eq(1, await s_optimize.main([dirn], outp=outp))

                self.eq(0, save.call_count)
                outp.expect('ERROR: compileall exited with code 2.')

    async def test_tools_utils_optimize_pyc(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'valu.py')
            with open(path, 'w') as fd:
                fd.write('valu = 10\n')

            pycpath = importlib.util.cache_from_source(path)
            self.false(s_optimize.isPycCurrent(path, pycpath))

            py_compile.compile(path, cfile=pycpath)
            self.true(s_optimize.isPycCurrent(path, pycpath))

            # a hash based bytecode file is current whatever the source timestamp
            py_compile.compile(path, cfile=pycpath, invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)
            os.utime(path, (0, 0))
            self.true(s_optimize.isPycCurrent(path, pycpath))

            with open(pycpath, 'r+b') as fd:
                fd.write(b'newp')
            self.false(s_optimize.isPycCurrent(path, pycpath))

            with open(pycpath, 'wb') as fd:
                fd.write(b'newp')
            self.false(s_optimize.isPycCurrent(path, pycpath))

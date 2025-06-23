import io
import os
import asyncio
import tarfile
import tempfile

from unittest import mock

import synapse.common as s_common

import synapse.lib.output as s_output

import synapse.tests.utils as s_t_utils

import synapse.tools.axon.dump as axon_dump
import synapse.tools.axon.load as axon_load

class AxonToolsTest(s_t_utils.SynTest):

    async def test_axon_dump_and_load_url_handling(self):
        with self.getTestDir() as testdir:
            argv = ['--url', 'cell:///definitelynotarealpath/axon', '--offset', '0', testdir]
            outp = s_output.OutPutStr()
            self.eq(1, await axon_dump.main(argv, outp=outp))
            self.isin('ERROR', str(outp))
            self.isin('Cell path does not exist', str(outp))

        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                tarfile = os.path.join(testdir, 'dummy.0-1.tar.gz')
                with open(tarfile, 'wb') as fd:
                    fd.write(b'dummy')
                url = f'cell://baduser:badpass@/{axon.dirn}'
                argv = ['--url', url, tarfile]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_load.main(argv, outp=outp))
                self.isin('No such user', str(outp))

        with self.getTestDir() as testdir:
            tarfile = os.path.join(testdir, 'dummy.0-1.tar.gz')
            with open(tarfile, 'wb') as fd:
                fd.write(b'dummy')
            argv = ['--url', 'cell:///definitelynotarealpath/axon', tarfile]
            outp = s_output.OutPutStr()
            self.eq(1, await axon_load.main(argv, outp=outp))
            self.isin('ERROR', str(outp))
            self.isin('Cell path does not exist', str(outp))

            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                url = f'cell://baduser:badpass@/{axon.dirn}'
                argv = ['--url', url, '--offset', '0', dumpdir]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_dump.main(argv, outp=outp))
                self.isin('No such user', str(outp))

    async def test_axon_dump_and_load(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon0')) as axon0:
                blobs = [b'foo', b'bar', b'baz' * 1000]
                sha2s = []
                for blob in blobs:
                    size, sha2 = await axon0.put(blob)
                    sha2s.append((size, sha2, blob))
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = [
                    '--url', f'cell:///{axon0.dirn}',
                    '--offset', '0',
                    dumpdir,
                ]
                self.eq(0, await axon_dump.main(argv))
                files = os.listdir(dumpdir)
                self.true(files, 'No dump file created')

                tarfiles = sorted([os.path.join(dumpdir, f) for f in files if f.endswith('.tar.gz')])
                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon1')) as axon1:
                    argv = ['--url', f'cell:///{axon1.dirn}'] + tarfiles
                    self.eq(0, await axon_load.main(argv))
                    for size, sha2, blob in sha2s:
                        self.true(await axon1.has(sha2))
                        out = b''
                        async for byts in axon1.get(sha2):
                            out += byts
                        self.eq(out, blob)

    async def test_dump_blob_size_mismatch(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                size, sha2 = await axon.put(b'hello world')
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                orig_get = axon.get
                async def bad_get(sha2arg, **kwargs):
                    if sha2arg == sha2:
                        yield b'hello' # corrupt it
                    else:
                        async for byts in orig_get(sha2arg):
                            yield byts
                axon.get = bad_get
                argv = ['--url', f'cell:///{axon.dirn}', '--offset', '0', dumpdir]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_dump.main(argv, outp=outp))
                self.isin('Blob size mismatch', str(outp))

    async def test_dump_not_axon_cell(self):
        with self.getTestDir() as testdir:
            async with self.getTestCore() as core:
                curl = core.getLocalUrl()
                argv = ['--url', curl, testdir]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_dump.main(argv, outp=outp))
                self.isin('only works on axon', str(outp))

    async def test_dump_outdir_is_not_directory(self):
        with self.getTestDir() as testdir:
            outpath = os.path.join(testdir, 'notadir')
            with open(outpath, 'w') as fd:
                fd.write('not a directory')
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                argv = ['--url', f'cell:///{axon.dirn}', '--offset', '0', outpath]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_dump.main(argv, outp=outp))
                self.isin('exists but is not a directory', str(outp))

    async def test_dump_rotate_size_and_load(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                blobs = [os.urandom(1024) for _ in range(10)]
                sha2s = []
                for blob in blobs:
                    size, sha2 = await axon.put(blob)
                    sha2s.append((size, sha2, blob))
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = ['--url', f'cell:///{axon.dirn}', '--offset', '0', '--rotate-size', '2048', dumpdir]
                outp = s_output.OutPutStr()
                self.eq(0, await axon_dump.main(argv, outp=outp))

                tarfiles = sorted([os.path.join(dumpdir, f) for f in os.listdir(dumpdir) if f.endswith('.tar.gz')])
                self.true(len(tarfiles) > 1)
                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon2')) as axon2:
                    argv = ['--url', f'cell:///{axon2.dirn}'] + tarfiles
                    self.eq(0, await axon_load.main(argv))
                    for size, sha2, blob in sha2s:
                        self.true(await axon2.has(sha2))
                        out = b''
                        async for byts in axon2.get(sha2):
                            out += byts
                        self.eq(out, blob)

    async def test_dump_statefile(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=testdir) as axon:
                blob_data = b'blobdata'
                await axon.put(blob_data)
                outdir = os.path.join(testdir, 'out')
                os.makedirs(outdir)
                statefile = os.path.join(testdir, 'state.yaml')

                argv = ['--url', axon.getLocalUrl(), '--statefile', statefile, outdir]
                outp = s_output.OutPutStr()
                self.eq(0, await axon_dump.main(argv, outp=outp))
                self.true(os.path.isfile(statefile))
                state = s_common.yamlload(statefile)
                self.isin('offset:next', state)

                s_common.yamlsave({'offset:next': 123}, statefile)
                outp = s_output.OutPutStr()
                self.eq(0, await axon_dump.main(argv, outp=outp))
                self.true(os.path.isfile(statefile))
                state = s_common.yamlload(statefile)
                self.isin('offset:next', state)
                self.ne(state['offset:next'], 123)

                statedir = os.path.join(testdir, 'statedir')
                os.makedirs(statedir)
                argv = ['--url', axon.getLocalUrl(), '--statefile', statedir, outdir]
                outp = s_output.OutPutStr()
                self.eq(0, await axon_dump.main(argv, outp=outp))
                cellinfo = await axon.getCellInfo()
                celliden = cellinfo['cell']['iden']
                statefile_path = os.path.join(statedir, f'{celliden}.yaml')
                self.true(os.path.isfile(statefile_path))
                state = s_common.yamlload(statefile_path)
                self.isin('offset:next', state)

    async def test_load_blobs_path_does_not_exist(self):
        with self.getTestDir() as testdir:
            missing = os.path.join(testdir, 'doesnotexist')
            argv = ['--url', 'cell:///definitelynotarealpath/axon', missing]
            outp = s_output.OutPutStr()
            self.eq(1, await axon_load.main(argv, outp=outp))
            self.isin('ERROR: Cell path does not exist', str(outp))

    async def test_load_continue_and_invalid_blob(self):
        with self.getTestDir() as testdir:
            tarpath = os.path.join(testdir, 'test1.tar.gz')
            with tarfile.open(tarpath, 'w:gz') as tar:
                info = tarfile.TarInfo('notablob.txt')
                data = b'not a blob'
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
                info2 = tarfile.TarInfo('invalidblobname.blob')
                data2 = b'data'
                info2.size = len(data2)
                tar.addfile(info2, io.BytesIO(data2))

            orig_uhex = s_common.uhex
            def fake_uhex(val):
                if val == 'invalidblobname':
                    raise Exception('bad hex')
                return orig_uhex(val)
            s_common.uhex = fake_uhex

            outp = s_output.OutPutStr()
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                argv = ['--url', axon.getLocalUrl(), tarpath]
                self.eq(0, await axon_load.main(argv, outp=outp))
            s_common.uhex = orig_uhex
            self.isin('Skipping invalid blob filename', str(outp))

    async def test_load_failed_to_extract(self):
        with self.getTestDir() as testdir:
            tarpath = os.path.join(testdir, 'test3.tar.gz')
            with tarfile.open(tarpath, 'w:gz') as tar:
                info = tarfile.TarInfo('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef.blob')
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            outp = s_output.OutPutStr()
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                argv = ['--url', axon.getLocalUrl(), tarpath]
                self.eq(0, await axon_load.main(argv, outp=outp))
            self.isin('Failed to extract', str(outp))

    async def test_load_not_axon_cell(self):
        with self.getTestDir() as testdir:
            async with self.getTestCore() as core:
                curl = core.getLocalUrl()
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = ['--url', curl, dumpdir]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_load.main(argv, outp=outp))
                self.isin('only works on axon', str(outp))

    async def test_load_oserror_extracting_blob(self):
        with self.getTestDir() as testdir:
            tarpath = os.path.join(testdir, 'test_oserror.tar.gz')
            with tarfile.open(tarpath, 'w:gz') as tar:
                info = tarfile.TarInfo('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef.blob')
                data = b'12345'
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            outp = s_output.OutPutStr()
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                with mock.patch('tarfile.TarFile.extractfile', side_effect=OSError("simulated extraction error")):
                    argv = ['--url', axon.getLocalUrl(), tarpath]
                    self.eq(0, await axon_load.main(argv, outp=outp))
            self.isin('WARNING: Error extracting', str(outp))

    async def test_load_skipping_existing_blob(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                blob = b'foo'
                size, sha2 = await axon.put(blob)
                tarpath = os.path.join(testdir, 'test2.tar.gz')
                with tarfile.open(tarpath, 'w:gz') as tar:
                    info = tarfile.TarInfo(f'{s_common.ehex(sha2)}.blob')
                    info.size = len(blob)
                    tar.addfile(info, io.BytesIO(blob))
                outp = s_output.OutPutStr()
                argv = ['--url', axon.getLocalUrl(), tarpath]
                self.eq(0, await axon_load.main(argv, outp=outp))
                self.isin('Skipping existing blob', str(outp))

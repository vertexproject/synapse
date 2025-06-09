import io
import os
import asyncio
import builtins

from unittest import mock

import synapse.common as s_common

import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils

import synapse.tools.axon.dump as axon_dump
import synapse.tools.axon.load as axon_load

class AxonToolsTest(s_t_utils.SynTest):

    async def test_axon_dump_and_load_args(self):
        argv = ['--wrong-size', '1000']
        outp = s_output.OutPutStr()
        self.eq(1, await axon_dump.main(argv, outp=outp))
        self.isin('usage: synapse.tools.axon.dump', str(outp))

        argv = ['--wrong-size', '1000']
        outp = s_output.OutPutStr()
        self.eq(1, await axon_load.main(argv, outp=outp))
        self.isin('usage: synapse.tools.axon.load', str(outp))

    async def test_axon_dump_and_load_url_handling(self):
        argv = ['--url', 'cell:///definitelynotarealpath/axon', '--offset', '0']
        outp = s_output.OutPutStr()
        self.eq(1, await axon_dump.main(argv, outp=outp))
        self.isin('Error', str(outp))
        self.isin('dumping blobs from Axon url', str(outp))

        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                blobsfile = os.path.join(testdir, 'dummy.0-1.blobs')
                with open(blobsfile, 'wb') as fd:
                    fd.write(s_msgpack.en(('blob:init', {})))
                url = f'cell://baduser:badpass@/{axon.dirn}'
                argv = ['--url', url, blobsfile]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_load.main(argv, outp=outp))
                self.isin('No such user', str(outp))

        with self.getTestDir() as testdir:
            blobsfile = os.path.join(testdir, 'dummy.0-1.blobs')
            with open(blobsfile, 'wb') as fd:
                fd.write(s_msgpack.en(('blob:init', {})))
            argv = ['--url', 'cell:///definitelynotarealpath/axon', blobsfile]
            outp = s_output.OutPutStr()
            self.eq(1, await axon_load.main(argv, outp=outp))
            self.isin('Error', str(outp))
            self.isin('loading blobs into Axon url', str(outp))

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
                dumpfile = os.path.join(dumpdir, files[0])
                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon1')) as axon1:
                    argv = [
                        '--url', f'cell:///{axon1.dirn}',
                        dumpfile,
                    ]
                    self.eq(0, await axon_load.main(argv))
                    for size, sha2, blob in sha2s:
                        self.true(await axon1.has(sha2))
                        out = b''
                        async for byts in axon1.get(sha2):
                            out += byts
                        self.eq(out, blob)

    async def test_dump_blob_sha256_mismatch(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                size, sha2 = await axon.put(b'hello world')
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                orig_get = axon.get
                async def bad_get(sha2arg, **kwargs):
                    if sha2arg == sha2:
                        yield b'x' * size  # corrrupt
                    else:
                        async for byts in orig_get(sha2arg):
                            yield byts
                axon.get = bad_get
                argv = ['--url', f'cell:///{axon.dirn}', '--offset', '0', dumpdir]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_dump.main(argv, outp=outp))
                self.isin('SHA256 mismatch', str(outp))

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

    async def test_dump_failed_to_close_file(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon')) as axon:
                await axon.put(b'foo')
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = ['--url', f'cell:///{axon.dirn}', '--offset', '0', dumpdir]
                real_open = builtins.open
                class BadFile(io.BytesIO):
                    def close(self):
                        raise OSError("cannot close file (test)")
                def bad_open(*args, **kwargs):
                    if args[0].endswith('.blobs'):
                        return BadFile()
                    return real_open(*args, **kwargs)
                with mock.patch('builtins.open', bad_open):
                    outp = s_output.OutPutStr()
                    self.eq(1, await axon_dump.main(argv, outp=outp))
                    self.isin("failed to close file", str(outp))

    async def test_dump_not_axon_cell(self):
        async with self.getTestCore() as core:
            curl = core.getLocalUrl()
            argv = ['--url', curl]
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
                files = sorted([f for f in os.listdir(dumpdir) if f.endswith('.blobs')])
                self.true(len(files) > 1)
                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon2')) as axon2:
                    files = [os.path.join(dumpdir, f) for f in os.listdir(dumpdir) if f.endswith('.blobs')]
                    argv = ['--url', f'cell:///{axon2.dirn}'] + files
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

    async def test_load_bad_sha256(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon0')) as axon0:
                size, sha2 = await axon0.put(b'hello world')
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = [
                    '--url', f'cell:///{axon0.dirn}',
                    '--offset', '0',
                    dumpdir,
                ]
                self.eq(0, await axon_dump.main(argv))

                dumpfile = os.path.join(dumpdir, os.listdir(dumpdir)[0])
                with open(dumpfile, 'rb') as fd:
                    items = list(s_msgpack.iterfd(fd))
                for i, item in enumerate(items):
                    if item[0] == 'blob':
                        meta = dict(item[1])
                        meta['sha256'] = '0' * 64  # corrupt it
                        items[i] = ('blob', meta)
                        break

                badfile = os.path.join(testdir, 'badfile.blobs')
                with open(badfile, 'wb') as fd:
                    for item in items:
                        fd.write(s_msgpack.en(item))

                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon1')) as axon1:
                    argv = [
                        '--url', f'cell:///{axon1.dirn}',
                        badfile,
                    ]
                    outp = s_output.OutPutStr()
                    self.eq(1, await axon_load.main(argv, outp=outp))
                    self.isin('ERROR: SHA256 mismatch', str(outp))

    async def test_load_blobs_path_does_not_exist(self):
        with self.getTestDir() as testdir:
            missing = os.path.join(testdir, 'doesnotexist')
            argv = ['--url', 'cell:///definitelynotarealpath/axon', missing]
            outp = s_output.OutPutStr()
            self.eq(1, await axon_load.main(argv, outp=outp))
            self.isin('No such file or directory', str(outp))

    async def test_load_missing_bytes(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon0')) as axon0:
                size, sha2 = await axon0.put(b'hello world')
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = [
                    '--url', f'cell:///{axon0.dirn}',
                    '--offset', '0',
                    dumpdir,
                ]
                self.eq(0, await axon_dump.main(argv))

                dumpfile = os.path.join(dumpdir, os.listdir(dumpdir)[0])
                with open(dumpfile, 'rb') as fd:
                    items = list(s_msgpack.iterfd(fd))

                for i, item in enumerate(items):
                    if type(item) is bytes:
                        items[i] = b'' # subtract a chunk, corrupt it
                        break
                badfile = os.path.join(testdir, 'badfile2.blobs')
                with open(badfile, 'wb') as fd:
                    for item in items:
                        fd.write(s_msgpack.en(item))

                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon1')) as axon1:
                    argv = [
                        '--url', f'cell:///{axon1.dirn}',
                        badfile,
                    ]
                    outp = s_output.OutPutStr()
                    self.eq(1, await axon_load.main(argv, outp=outp))
                    self.isin('ERROR: Blob size mismatch', str(outp))

    async def test_load_no_blobs_files_found(self):
        with self.getTestDir() as testdir:
            argv = ['--url', 'cell:///definitelynotarealpath/axon', testdir]
            outp = s_output.OutPutStr()
            self.eq(1, await axon_load.main(argv, outp=outp))
            self.isin('No such file or directory', str(outp))

    async def test_load_not_axon_cell(self):
        with self.getTestDir() as testdir:
            async with self.getTestCore() as core:
                curl = core.getLocalUrl()
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                with open(os.path.join(dumpdir, 'aabbccddeeff00112233445566778899.0-0.blobs'), 'wb') as f:
                    f.write(b'newp')
                argv = ['--url', curl, dumpdir]
                outp = s_output.OutPutStr()
                self.eq(1, await axon_load.main(argv, outp=outp))
                self.isin('only works on axon', str(outp))

    async def test_load_unexpected_eof(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon0')) as axon0:
                size, sha2 = await axon0.put(b'hello world')
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = ['--url', f'cell:///{axon0.dirn}', '--offset', '0', dumpdir]
                self.eq(0, await axon_dump.main(argv))

                dumpfile = os.path.join(dumpdir, os.listdir(dumpdir)[0])
                with open(dumpfile, 'rb') as fd:
                    items = list(s_msgpack.iterfd(fd))
                for i in range(len(items) - 1, -1, -1):
                    if type(items[i]) is bytes:
                        items = items[:i]
                        break
                badfile = os.path.join(testdir, 'badfile_eof.blobs')
                with open(badfile, 'wb') as fd:
                    for item in items:
                        fd.write(s_msgpack.en(item))

                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon1')) as axon1:
                    argv = ['--url', f'cell:///{axon1.dirn}', badfile]
                    outp = s_output.OutPutStr()
                    self.eq(1, await axon_load.main(argv, outp=outp))
                    self.isin('Unexpected end of file while reading blob', str(outp))

    async def test_load_unexpected_message_type(self):
        with self.getTestDir() as testdir:
            async with self.getTestAxon(dirn=os.path.join(testdir, 'axon0')) as axon0:
                size, sha2 = await axon0.put(b'hello world')
                dumpdir = os.path.join(testdir, 'dumpdir')
                os.makedirs(dumpdir)
                argv = ['--url', f'cell:///{axon0.dirn}', '--offset', '0', dumpdir]
                self.eq(0, await axon_dump.main(argv))

                dumpfile = os.path.join(dumpdir, os.listdir(dumpdir)[0])
                with open(dumpfile, 'rb') as fd:
                    items = list(s_msgpack.iterfd(fd))
                items.insert(1, ('unexpected', {'foo': 'bar'}))
                badfile = os.path.join(testdir, 'badfile_unexpected.blobs')
                with open(badfile, 'wb') as fd:
                    for item in items:
                        fd.write(s_msgpack.en(item))

                async with self.getTestAxon(dirn=os.path.join(testdir, 'axon1')) as axon1:
                    argv = ['--url', f'cell:///{axon1.dirn}', badfile]
                    outp = s_output.OutPutStr()
                    self.eq(1, await axon_load.main(argv, outp=outp))
                    self.isin('ERROR: Unexpected message type', str(outp))

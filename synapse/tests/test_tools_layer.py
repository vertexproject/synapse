import os

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_test

import synapse.tools.layer.dump as s_t_dump
import synapse.tools.layer.load as s_t_load

class LayerTest(s_test.SynTest):

    async def test_tools_layer_dump(self):

        async with self.getTestCore() as core:

            url = core.getLocalUrl()

            layr00 = await core.addLayer()
            layr00iden = layr00.get('iden')
            view00 = await core.addView({'layers': [layr00iden]})

            soffs = await core.getNexsIndx()

            opts = {'view': view00.get('iden')}
            nodes = await core.nodes('[ inet:ipv4=192.168.1.0/24 ]', opts=opts)
            self.len(256, nodes)

            eoffs = soffs + 256

            chunksize = 10

            with self.getTestDir() as dirn:
                # Handle no edits from offset
                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    '--outdir', dirn,
                    '--offset', '10000',
                    layr00iden,
                )

                outp = s_output.OutPutStr()
                self.eq(1, await s_t_dump.main(argv, outp=outp))
                self.isin(f'ERROR: No edits to export starting from offset (10000).', str(outp))

                # Handle outdir being an existing file
                filename = s_common.genpath(dirn, 'newp')
                s_common.genfile(filename).close()

                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    '--outdir', filename,
                    layr00iden,
                )

                outp = s_output.OutPutStr()
                self.eq(1, await s_t_dump.main(argv, outp=outp))
                self.isin(f'ERROR: Specified output directory {filename} exists but is not a directory.', str(outp))

                # Handle requested starting offset being different than returned offset
                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    '--outdir', dirn,
                    '--offset', str(soffs - 1),
                    layr00iden,
                )

                outp = s_output.OutPutStr()
                self.eq(1, await s_t_dump.main(argv, outp=outp))
                self.isin(f'ERROR: First offset ({soffs}) differs from requested starting offset ({soffs - 1}).', str(outp))

                # Happy path
                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    '--outdir', dirn,
                    '--offset', str(soffs),
                    layr00iden,
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_dump.main(argv, outp=outp))
                self.isin(f'Successfully exported layer {layr00iden} from cortex {core.iden}.', str(outp))

                for ii in range(soffs, eoffs - chunksize, chunksize):
                    path = s_common.genpath(dirn, f'{core.iden}.{layr00iden}.{ii}-{ii + chunksize - 1}.nodeedits')
                    self.true(os.path.exists(path))

                # Open and inspect first file
                filename = f'{core.iden}.{layr00iden}.{soffs}-{soffs + 9}.nodeedits'
                msgs = list(s_msgpack.iterfile(s_common.genpath(dirn, filename)))
                self.len(12, msgs)

                self.eq(msgs[0][0], 'init')
                self.eq(msgs[0][1].get('hdrvers'), 1)
                self.eq(msgs[0][1].get('celliden'), core.iden)
                self.eq(msgs[0][1].get('layriden'), layr00iden)
                self.eq(msgs[0][1].get('offset'), soffs)
                self.eq(msgs[0][1].get('chunksize'), chunksize)
                self.nn(msgs[0][1].get('tick'))
                self.isinstance(msgs[0][1].get('tick'), int)
                self.eq(msgs[0][1].get('cellvers'), core.cellinfo.get('cell:version'))

                for msg in msgs[1:-1]:
                    self.len(2, msg)
                    self.eq(msg[0], 'edit')
                    self.len(3, msg[1])

                self.eq(msgs[11][0], 'fini')
                self.eq(msgs[11][1].get('offset'), soffs + 9)
                self.nn(msgs[11][1].get('tock'))
                self.isinstance(msgs[11][1].get('tock'), int)

    async def test_tools_layer_load(self):
        async with self.getTestCore() as core:

            url = core.getLocalUrl()

            layr00 = await core.addLayer()
            layr00iden = layr00.get('iden')
            view00 = await core.addView({'layers': [layr00iden]})

            layr01 = await core.addLayer()
            layr01iden = layr01.get('iden')
            view01 = await core.addView({'layers': [layr01iden]})

            soffs = await core.getNexsIndx()

            opts = {'view': view00.get('iden')}
            nodes = await core.nodes('[ inet:ipv4=192.168.1.0/24 ]', opts=opts)
            self.len(256, nodes)

            eoffs = soffs + 256

            with self.getTestDir() as dirn:
                # Export layr00
                argv = (
                    '--url', url,
                    '--outdir', dirn,
                    layr00iden,
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_dump.main(argv, outp=outp))
                self.isin(f'Successfully exported layer {layr00iden} from cortex {core.iden}.', str(outp))

                # Verify layr01 is empty
                opts = {'view': view01.get('iden')}
                nodes = await core.nodes('inet:ipv4', opts=opts)
                self.len(0, nodes)

                files = [os.path.join(dirn, k) for k in os.listdir(dirn)]
                self.len(1, files)

                # Import to layr01
                argv = (
                    '--url', url,
                    layr01iden,
                    files[0],
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_load.main(argv, outp=outp))
                self.isin('Processing the following nodeedits:', str(outp))
                self.isin(f'{soffs:<16d} | {files[0]}', str(outp))
                self.isin(f'Processing {files[0]}, offset={soffs}, tick=', str(outp))
                self.isin(f'Completed {files[0]} with {eoffs - soffs} edits ({soffs} - {eoffs - 1}).', str(outp))

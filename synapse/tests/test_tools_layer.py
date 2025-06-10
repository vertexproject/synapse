import os

import synapse.common as s_common

import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

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
                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    '--offset', str(soffs),
                    layr00iden,
                    dirn,
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_dump.main(argv, outp=outp))
                self.isin(f'Successfully exported layer {layr00iden}.', str(outp))

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

            # Test state tracking
            with self.getTestDir() as dirn:
                # Check state file is written
                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    '--offset', str(soffs),
                    layr00iden,
                    dirn,
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_dump.main(argv, outp=outp))
                self.isin(f'Successfully exported layer {layr00iden}.', str(outp))

                state = s_common.yamlload(dirn, f'{core.iden}.{layr00iden}.yaml')
                self.eq(state, {'offset:next': eoffs})

                # Check state file is read
                opts = {'view': view00.get('iden')}
                nodes = await core.nodes('[ inet:ipv4=10.0.0.0/24 ]', opts=opts)
                self.len(256, nodes)

                state = {'offset:next': eoffs + 1}
                statefile = s_common.genpath(dirn, 'state.yaml')
                s_common.yamlsave(state, statefile)

                argv = (
                    '--url', url,
                    '--statefile', statefile,
                    layr00iden,
                    s_common.genpath(dirn, 'next'),
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_dump.main(argv, outp=outp))
                self.isin(f'Successfully exported layer {layr00iden}.', str(outp))

                state = s_common.yamlload(dirn, statefile)
                self.eq(state, {'offset:next': eoffs + 256})

    async def test_tools_layer_dump_errors(self):

        # Non-cortex cell
        async with self.getTestCell() as cell:
            with self.getTestDir() as dirn:
                with s_common.genfile(dirn, 'newp') as fd:
                    filename = fd.name
                    fd.write(s_msgpack.en(('init', {'offset': 0, 'cellvers': s_version.version})))

                url = cell.getLocalUrl()
                argv = ('--url', url, s_common.guid(), dirn)
                outp = s_output.OutPutStr()
                self.eq(1, await s_t_dump.main(argv, outp=outp))
                self.isin(f'ERROR: Layer dump tool only works on cortexes, not cell.', str(outp))

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
                    '--offset', '9000',
                    layr00iden,
                    dirn,
                )

                outp = s_output.OutPutStr()
                self.eq(1, await s_t_dump.main(argv, outp=outp))
                self.isin(f'ERROR: No edits to export starting from offset (9000).', str(outp))

                # Handle outdir being an existing file
                filename = s_common.genpath(dirn, 'newp')
                s_common.genfile(filename).close()

                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    layr00iden,
                    filename,
                )

                outp = s_output.OutPutStr()
                self.eq(1, await s_t_dump.main(argv, outp=outp))
                self.isin(f'ERROR: Specified output directory {filename} exists but is not a directory.', str(outp))

                # Invalid layer iden
                newpiden = s_common.guid()
                argv = (
                    '--url', url,
                    '--chunksize', str(chunksize),
                    newpiden,
                    dirn,
                )

                outp = s_output.OutPutStr()
                self.eq(1, await s_t_dump.main(argv, outp=outp))
                self.isin(f'ERROR: No such layer {newpiden}.', str(outp))

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
                    layr00iden,
                    dirn,
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_dump.main(argv, outp=outp))
                self.isin(f'Successfully exported layer {layr00iden}.', str(outp))

                # Verify layr01 is empty
                opts = {'view': view01.get('iden')}
                nodes = await core.nodes('inet:ipv4', opts=opts)
                self.len(0, nodes)

                files = [os.path.join(dirn, k) for k in os.listdir(dirn) if k.endswith('.nodeedits')]
                self.len(1, files)

                # Import to layr01
                argv = (
                    '--url', url,
                    '--dryrun',
                    layr01iden,
                    files[0],
                )

                outp = s_output.OutPutStr()
                self.eq(0, await s_t_load.main(argv, outp=outp))
                self.isin('Processing the following nodeedits:', str(outp))
                self.isin(f'{soffs:<16d} | {files[0]}', str(outp))
                self.isin(f'Loading {files[0]}, offset={soffs}, tick=', str(outp))
                self.isin(f'Successfully loaded {files[0]} with {eoffs - soffs} edits ({soffs} - {eoffs - 1}).', str(outp))

                # Verify layr01 is empty
                opts = {'view': view01.get('iden')}
                nodes = await core.nodes('inet:ipv4', opts=opts)
                self.len(0, nodes)

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
                self.isin(f'Loading {files[0]}, offset={soffs}, tick=', str(outp))
                self.isin(f'Successfully loaded {files[0]} with {eoffs - soffs} edits ({soffs} - {eoffs - 1}).', str(outp))

                # Verify layr01 has data now
                opts = {'view': view01.get('iden')}
                nodes = await core.nodes('inet:ipv4', opts=opts)
                self.len(256, nodes)

    async def test_tools_layer_load_errors(self):

        iden = s_common.guid()

        # Non-cortex cell
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'newp') as fd:
                filename = fd.name
                fd.write(s_msgpack.en(('init', {'offset': 0, 'cellvers': s_version.version})))

            async with self.getTestCell() as cell:
                url = cell.getLocalUrl()
                argv = ('--url', url, iden, filename)
                outp = s_output.OutPutStr()
                self.eq(1, await s_t_load.main(argv, outp=outp))
                self.isin(f'ERROR: Layer load tool only works on cortexes, not cell.', str(outp))

        # Non-existent file
        argv = (iden, 'newp')
        outp = s_output.OutPutStr()
        self.eq(1, await s_t_load.main(argv, outp=outp))
        self.isin('Invalid input file specified: newp.', str(outp))

        # Input file is a directory
        with self.getTestDir() as dirn:
            argv = (iden, dirn)
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_load.main(argv, outp=outp))
            self.isin(f'Invalid input file specified: {dirn}.', str(outp))

        # Input file doesn't have an init message first
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'noinit.nodeedits') as fd:
                filename = fd.name
                fd.write(s_msgpack.en(('newp', {})))

            argv = (iden, filename)
            outp = s_output.OutPutStr()
            self.eq(1, await s_t_load.main(argv, outp=outp))
            self.isin(f'Invalid header in {filename}.', str(outp))

        # Invalid/too high cell version
        with self.getTestDir() as dirn:
            version = (99, 99, 0)
            verstr = '.'.join(map(str, version))

            with s_common.genfile(dirn, 'cellvers00.nodeedits') as fd:
                file00 = fd.name
                fd.write(s_msgpack.en(('init', {'offset': 0, 'cellvers': s_version.version})))

            with s_common.genfile(dirn, 'cellvers01.nodeedits') as fd:
                file01 = fd.name
                fd.write(s_msgpack.en(('init', {'offset': 0, 'cellvers': version})))

            async with self.getTestCore() as core:
                url = core.getLocalUrl()
                argv = ('--url', url, iden, file00, file01)
                outp = s_output.OutPutStr()
                self.eq(1, await s_t_load.main(argv, outp=outp))
                self.isin(f'Synapse version mismatch ({s_version.verstring} < {verstr}).', str(outp))

        # Invalid message type
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'badtype.nodeedits') as fd:
                filename = fd.name
                fd.write(s_msgpack.en((
                    'init',
                    {
                        'hdrvers': 1,
                        'celliden': s_common.guid(),
                        'layriden': s_common.guid(),
                        'offset': 0,
                        'chunksize': 10000,
                        'tick': s_common.now(),
                        'cellvers': s_version.version,
                    }
                )))

                fd.write(s_msgpack.en(('newp', {})))

            async with self.getTestCore() as core:
                url = core.getLocalUrl()
                layriden = core.getView().layers[0].iden
                argv = ('--url', url, layriden, filename)
                outp = s_output.OutPutStr()
                self.eq(1, await s_t_load.main(argv, outp=outp))
                self.isin('Unexpected message type: newp.', str(outp))

        # Missing fini
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'badtype.nodeedits') as fd:
                filename = fd.name
                fd.write(s_msgpack.en((
                    'init',
                    {
                        'hdrvers': 1,
                        'celliden': s_common.guid(),
                        'layriden': s_common.guid(),
                        'offset': 0,
                        'chunksize': 10000,
                        'tick': s_common.now(),
                        'cellvers': s_version.version,
                    }
                )))

            async with self.getTestCore() as core:
                url = core.getLocalUrl()
                layriden = core.getView().layers[0].iden
                argv = ('--url', url, layriden, filename)
                outp = s_output.OutPutStr()
                self.eq(1, await s_t_load.main(argv, outp=outp))
                self.isin(f'Incomplete/corrupt export: {filename}.', str(outp))

        # Fini offset mismatch
        with self.getTestDir() as dirn:
            soffs = 0
            eoffs = 1000
            with s_common.genfile(dirn, 'badtype.nodeedits') as fd:
                filename = fd.name
                fd.write(s_msgpack.en((
                    'init',
                    {
                        'hdrvers': 1,
                        'celliden': s_common.guid(),
                        'layriden': s_common.guid(),
                        'offset': soffs,
                        'chunksize': 10000,
                        'tick': s_common.now(),
                        'cellvers': s_version.version,
                    }
                )))

                fd.write(s_msgpack.en((
                    'fini',
                    {
                        'offset': eoffs,
                        'tock': s_common.now(),
                    }
                )))

            async with self.getTestCore() as core:
                url = core.getLocalUrl()
                layriden = core.getView().layers[0].iden
                argv = ('--url', url, layriden, filename)
                outp = s_output.OutPutStr()
                self.eq(1, await s_t_load.main(argv, outp=outp))
                self.isin(f'Incomplete/corrupt export: {filename}. Expected offset {eoffs}, got {soffs}.', str(outp))

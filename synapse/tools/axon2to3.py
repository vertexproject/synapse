import os
import sys
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cmd as s_cmd
import synapse.lib.cell as s_cell
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

async def migrate_history(dirn, outp=s_output.stdout):

    path = os.path.join(dirn, 'axon.lmdb')

    with s_common.getTempDir() as tmpdir:
        temp_path = os.path.join(tmpdir, 'axon.lmdb')

        async with await s_lmdbslab.Slab.anit(path) as slab:
            hist = s_lmdbslab.Hist(slab, 'history')
            count = 0
            with open(temp_path, 'wb') as tmpfile:
                for tick, item in hist.carve(0):
                    tmpfile.write(s_msgpack.en((tick, item)))
                    count += 1
            outp.printf(f"Found {count} history rows.")
            slab.dropdb('history')

        async with await s_lmdbslab.Slab.anit(path) as slab:
            hist = s_lmdbslab.Hist(slab, 'history')
            migrated = 0
            with open(temp_path, 'rb') as tmpfile:
                for tick, item in s_msgpack.iterfd(tmpfile):
                    if tick < 1e15:
                        newtick = tick * 1000
                    else:
                        newtick = tick
                    hist.add(item, tick=newtick)
                    migrated += 1
            outp.printf(f"Migrated {migrated} history rows in total.")

    return 0

async def main(argv, outp=s_output.stdout):
    pars = s_cmd.Parser(prog='synapse.tools.axon2to3', outp=outp)
    pars.add_argument('dirn', help='The directory of the Axon.')

    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit:
        return 0

    try:
        async with await s_cell.Cell.anit(opts.dirn) as cell:
            vers = cell.cellvers.get('axon:history', 0)
            if vers < 1:
                await migrate_history(opts.dirn, outp)
                await cell.setCellVers('axon:history', vers + 1, False)
            else:
                outp.printf("Migration already done.")
    except s_exc.SlabAlreadyOpen:
        outp.printf("ERROR: The Axon appears to be running. Please stop the Axon service before running this tool.")
        return 1
    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))

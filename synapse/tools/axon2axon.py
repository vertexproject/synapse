import sys
import asyncio
import logging

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.exc as s_exc
import synapse.lib.cmd as s_cmd
import synapse.lib.base as s_base
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.axon2axon', outp=outp)
    pars.add_argument('--offset', type=int, default=0, help='An offset within the source axon to start from.')
    pars.add_argument('src_axon', help='The telepath URL of the source axon.')
    pars.add_argument('dst_axon', help='The telepath URL of the destination axon.')

    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit:
        return 1

    async with s_telepath.withTeleEnv():
        async with await s_base.Base.anit() as base:

            srcaxon = await base.enter_context(await s_telepath.openurl(opts.src_axon))
            dstaxon = await base.enter_context(await s_telepath.openurl(opts.dst_axon))

            outp.printf(f'Starting transfer at offset: {opts.offset}')

            async for (offs, (sha256, size)) in srcaxon.hashes(opts.offset):
                offstext = str(offs).rjust(10)
                sha2text = s_common.ehex(sha256)
                outp.printf(f'[{offstext}] - {sha2text} ({size})')
                async with await dstaxon.upload() as fd:
                    async for byts in srcaxon.get(sha256):
                        await fd.write(byts)
                    await fd.save()
    return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))

import sys
import asyncio
import logging
import argparse

import synapse.common as s_common

import synapse.lib.coro as s_coro
import synapse.lib.output as s_output
import synapse.lib.rstorm as s_rstorm

logger = logging.getLogger(__name__)

prog = 'synapse.tools.rstorm'
descr = 'An RST pre-processor that allows you to embed storm directives.'

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog=prog, description=descr)
    pars.add_argument('rstfile', help='Input RST file with storm directives.')
    pars.add_argument('--save', help='Output file to save (default: stdout)')

    opts = pars.parse_args(argv)

    async with await s_rstorm.StormRst.anit(opts.rstfile) as rstorm:
        lines = await rstorm.run()

    if opts.save:
        with open(s_common.genpath(opts.save), 'w') as fd:
            fd.truncate(0)
            [fd.write(line) for line in lines]
    else:
        for line in lines:
            outp.printf(line, addnl=False)

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    s_common.setlogging(logger)
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':
    sys.exit(asyncio.run(_main(sys.argv[1:])))

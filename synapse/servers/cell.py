# pragma: no cover
import sys
import asyncio

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps

async def main(argv, outp=s_output.stdout):

    outp.printf(f'Resolving cellpath: {argv[0]}')
    ctor = s_dyndeps.getDynLocal(argv[0])
    if ctor is None:
        raise s_exc.NoSuchCtor(name=argv[0], mesg='No Cell ctor found.')

    return await ctor.initFromArgv(argv[1:], outp=outp)

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))

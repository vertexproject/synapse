import os
import sys
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps

def getStemCell(dirn):

    if not os.path.isdir(dirn):
        mesg = f'Directory {dirn} does not exist!'
        raise s_exc.NoSuchDir(mesg=mesg)

    ctorname = os.getenv('SYN_STEM_CELL_CTOR')

    cellyaml = os.path.join(dirn, 'cell.yaml')

    if os.path.isfile(cellyaml):
        conf = s_common.yamlload(cellyaml)
        ctorname = conf.get('cell:ctor', ctorname)

    if ctorname is not None:
        ctorname = ctorname.strip()
        ctor = s_dyndeps.getDynLocal(ctorname)
        if ctor is None:
            raise s_exc.NoSuchCtor(mesg=f'Unable to resolve ctor [{ctorname}]', ctor=ctorname)
        return ctor

    mesg = f'No such file: {cellyaml} and SYN_STEM_CELL_CTOR environmt variable is not set.'
    raise s_exc.NoSuchFile(mesg=mesg, path=cellyaml)

async def main(argv, outp=s_output.stdout):  # pragma: no cover
    ctor = getStemCell(argv[0])
    return await ctor.execmain(argv, outp=outp)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))

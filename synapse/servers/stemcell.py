import os
import sys
import asyncio

import synapse.common as s_common
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps

def getStemCell(dirn):

    if not os.path.isdir(dirn):
        mesg = f'Directory {dirn} does not exist!'
        raise s_exc.NoSuchDir(mesg=mesg)

    cellyaml = os.path.join(dirn, 'cell.yaml')
    if not os.path.isfile(cellyaml):
        mesg = f'No such file: {cellyaml}'
        raise s_exc.NoSuchFile(mesg=mesg)

    conf = s_common.yamlload(cellyaml)
    ctorname = conf.get('cell:ctor')

    return s_dyndeps.getDynLocal(ctorname.strip())

#pragma: no cover
async def main(argv, outp=s_output.stdout):
    ctor = getStemCell(argv[0])
    return await ctor.execmain(argv, outp=outp)

#pragma: no cover
if __name__ == '__main__':
    sys.exit(asyncio.run(main(sys.argv[1:])))

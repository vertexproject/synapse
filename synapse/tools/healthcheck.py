import sys
import json
import asyncio

import synapse.exc as s_exc
import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.telepath as s_telepath

def serialize(ret):
    s = json.dumps(ret, separators=(',', ':'))
    return s

async def main(argv, outp=s_output.stdout):
    pars = makeargparser()
    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit as e:
        return e.get('status')

    try:
        prox = await asyncio.wait_for(s_telepath.openurl(opts.cell),
                                      timeout=opts.timeout)
    except ConnectionError as e:
        ret = (False, {'mesg': 'Unable to  connecting to cell',
                       'errname': e.__class__.__name__,
                       'errmesg': str(e),
                       'cell': opts.cell})
        outp.printf(serialize(ret))
        return 1
    except asyncio.CancelledError as e:
        ret = (False, {'mesg': 'Timeout connecting to cell',
                       'errname': e.__class__.__name__,
                       'errmesg': str(e),
                       'cell': opts.cell})
        outp.printf(serialize(ret))
        return 1

    try:
        ret = await asyncio.wait_for(prox.getHealthCheck(),
                                     timeout=opts.timeout)
    except s_exc.SynErr as e:
        # TODO FIX ME!
        print(e)
        ret = (False, {'mesg': 'Synapse error encountered.',
                       'errname': e.__class__.__name__,
                       'errmesg': e.get('mesg'),
                       'cell': opts.cell})

    except asyncio.CancelledError as e:
        ret = (False, {'mesg': 'Timeout getting health information from cell',
                       'errname': e.__class__.__name__,
                       'errmesg': str(e),
                       'cell': opts.cell})

    finally:
        await prox.fini()

    retval = 1
    if ret[0] is True:
        retval = 0

    outp.printf(serialize(ret))
    return retval

def makeargparser():
    desc = '''
    synapse healthcheck tool
    '''
    pars = s_cmd.Parser('healthcheck', description=desc)
    pars.add_argument('--cell', '-c', required=True, type=str,
                      help='Telepath path to the cell to check.')
    pars.add_argument('--timeout', '-t', default=30, type=int,
                      help='Connection/call timeout')
    return pars

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(main(sys.argv[1:]))

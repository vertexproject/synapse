import sys
import json
import socket
import asyncio

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output
import synapse.lib.health as s_health

def serialize(ret):
    s = json.dumps(ret, separators=(',', ':'))
    return s

def format_component(e, mesg: str) -> dict:
    d = {
        'name': 'error',
        'status': s_health.FAILED,
        'mesg': mesg,
        'data': {
            'errname': e.__class__.__name__,
            'errmesg': str(e),
        }
    }

    return d

async def main(argv, outp=s_output.stdout):
    pars = makeargparser()
    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit as e:  # pragma: no cover
        return e.get('status')

    try:
        prox = await asyncio.wait_for(s_telepath.openurl(opts.cell),
                                      timeout=opts.timeout)
    except (ConnectionError, socket.gaierror) as e:
        mesg = 'Unable to connect to cell.'
        ret = {'status': 'failed',
               'iden': opts.cell,
               'components': [format_component(e, mesg)],
               }
        outp.printf(serialize(ret))
        return 1
    except s_exc.SynErr as e:
        mesg = 'Synapse error encountered.'
        ret = {'status': s_health.FAILED,
               'iden': opts.cell,
               'components': [format_component(e, mesg)],
               }
        outp.printf(serialize(ret))
        return 1
    except asyncio.TimeoutError as e:  # pragma: no cover
        mesg = 'Timeout connecting to cell'
        ret = {'status': s_health.FAILED,
               'iden': opts.cell,
               'components': [format_component(e, mesg)],
               }
        outp.printf(serialize(ret))
        return 1

    try:
        ret = await asyncio.wait_for(prox.getHealthCheck(),
                                     timeout=opts.timeout)
    except s_exc.SynErr as e:
        mesg = 'Synapse error encountered.'
        ret = {'status': s_health.FAILED,
               'iden': opts.cell,
               'components': [format_component(e, mesg)],
               }

    except asyncio.TimeoutError as e:
        mesg = 'Timeout getting health information from cell.'
        ret = {'status': s_health.FAILED,
               'iden': opts.cell,
               'components': [format_component(e, mesg)],
               }

    finally:
        await prox.fini()

    retval = 1
    if ret.get('status') in (s_health.NOMINAL, s_health.DEGRADED):
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
    pars.add_argument('--timeout', '-t', default=10, type=float,
                      help='Connection and call timeout')
    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:])))

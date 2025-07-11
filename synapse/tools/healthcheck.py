import socket
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.health as s_health
import synapse.lib.urlhelp as s_urlhelp

def serialize(ret):
    return s_json.dumps(ret).decode()

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
    pars = getArgParser(outp)
    try:
        opts = pars.parse_args(argv)
    except s_exc.ParserExit as e:  # pragma: no cover
        return e.get('status')

    url = opts.cell
    sanitized_url = s_urlhelp.sanitizeUrl(url)

    try:
        async with s_telepath.withTeleEnv():

            prox = await s_common.wait_for(s_telepath.openurl(url),
                                           timeout=opts.timeout)
    except (s_exc.LinkErr, s_exc.NoSuchPath, socket.gaierror) as e:
        mesg = f'Unable to connect to cell @ {sanitized_url}.'
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
        ret = await s_common.wait_for(prox.getHealthCheck(),
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

def getArgParser(outp):
    desc = '''
    synapse healthcheck tool
    '''
    pars = s_cmd.Parser(prog='synapse.tools.healthcheck', outp=outp, description=desc)
    pars.add_argument('--cell', '-c', required=True, type=str,
                      help='Telepath path to the cell to check.')
    pars.add_argument('--timeout', '-t', default=10, type=float,
                      help='Connection and call timeout')
    return pars

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)

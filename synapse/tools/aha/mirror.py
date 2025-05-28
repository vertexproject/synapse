import sys
import asyncio
import argparse
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.output as s_output
import synapse.lib.version as s_version

descr = '''
Query the AHA server for the service cluster status of mirrors.

Examples:

    python -m synapse.tools.aha.mirror --timeout 30

'''
def timeout_type(valu):
    try:
        ivalu = int(valu)
        if ivalu < 0:
            raise ValueError
    except ValueError:
        raise s_exc.BadArg(mesg=f"{valu} is not a valid non-negative integer")
    return ivalu

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.mirror', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--timeout', type=timeout_type, default=10, help='The timeout in seconds for individual service API calls')
    pars.add_argument('--wait', action='store_true', help='Whether to wait for the mirrors to sync.')
    opts = pars.parse_args(argv)

    async with s_telepath.withTeleEnv():
        try:
            async with await s_telepath.openurl(opts.url) as prox:

                classes = prox._getClasses()

                # FIXME we need a less fragile way to do this
                if 'synapse.lib.aha.AhaApi' not in classes:
                    outp.printf(f'Service at {opts.url} is not an AHA server')
                    return 1

                virtuals = {}
                mirrors = collections.defaultdict(list)

                async for svcdef in prox.getAhaSvcs():

                    name = svcdef.get('name')
                    urlinfo = svcdef.get('urlinfo', {})

                    hostname = urlinfo.get('hostname')
                    if hostname is None:
                        continue

                    leader = svcdef.get('leader')
                    if leader is None:
                        continue

                    print(f'SVCDEF {svcdef}')

                    cellinfo = None
                    if svcdef.get('online') is not None:
                        cellinfo = await prox.callAhaSvcApi(realsvc.get('name'), todo, timeout=opts.timeout)

                    if name != hostname:
                        virtuals[name] = svcdef
                    else:
                        mirrors[name].append(svcdef)

                todo = s_common.todo('getCellInfo')

                for virtname, svcdef in virtuals.items():

                    iden = svcdef.get('iden')
                    leader = svcdef.get('leader')

                    svcdefs = mirrors.get(name)
                    if svcdefs is None:
                        continue

                    oupt.printf('Mirror Group: {virtname}')
                    outp.printf('{"Name":<40} {"Leader":<10} {"Ready":<7} {"Host":<16} {"Port":<5} {"Version":<12} {"Synapse":<12} {"Nexus Index":<11}')
                    for realsvc in svcdefs:

                        online = realsvc.get('online')

                        ready = str(realsvc.get('ready')).lower()
                        port = realsvc['urlinfo'].get('port')
                        hostname = realsvc['urlinfo'].get('hostname')

                        nexsindx = '<offline>'
                        isleader = '<offline>'

                        if online is not None:

                            cellinfo = await prox.callAhaSvcApi(realsvc.get('name'), todo, timeout=opts.timeout)

                            nexsindx = str(cellinfo.get('nexsindx'))
                            isleader = str(cellinfo.get('uplink') is None).lower()

                        outp.printf(f'{name:<40} {isleader:<10} {ready:<7} {hostname:<32} {port:<5} {version:<12} {synvers:<12} {nexsindx:<11}')

                    outp.printf('')

                return 0

        except Exception as e:
            mesg = repr(e)
            if isinstance(e, s_exc.SynErr):
                mesg = e.errinfo.get('mesg', repr(e))
            outp.printf(f'ERROR: {mesg}')
            return 1

async def _main(argv, outp=s_output.stdout):  # pragma: no cover
    ret = await main(argv, outp=outp)
    await asyncio.wait_for(s_coro.await_bg_tasks(), timeout=60)
    return ret

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(_main(sys.argv[1:])))

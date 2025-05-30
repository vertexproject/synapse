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
        raise s_exc.BadArg(mesg=f"{valu} must be a positive integer")
    return ivalu

async def main(argv, outp=s_output.stdout):

    pars = argparse.ArgumentParser(prog='synapse.tools.aha.mirror', description=descr,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    pars.add_argument('--url', default='cell:///vertex/storage', help='The telepath URL to connect to the AHA service.')
    pars.add_argument('--timeout', type=timeout_type, default=10, help='The timeout in seconds for individual service API calls')
    pars.add_argument('--wait', action='store_true', help='Whether to wait for the mirrors to sync.')

    async with s_telepath.withTeleEnv():

        try:

            opts = pars.parse_args(argv)

            async with await s_telepath.openurl(opts.url) as prox:

                classes = prox._getClasses()

                # FIXME we need a less fragile way to do this
                if 'synapse.lib.aha.AhaApi' not in classes:
                    outp.printf(f'Service at {opts.url} is not an AHA server')
                    return 1

                todo = s_common.todo('getCellInfo')

                runs = {} # iden -> svcdef (only for name == hostname )
                virtuals = collections.defaultdict(list)
                clusters = collections.defaultdict(list)

                async for svcdef in prox.getAhaSvcs():

                    iden = svcdef.get('iden')
                    name = svcdef.get('name')
                    urlinfo = svcdef.get('urlinfo', {})

                    hostname = urlinfo.get('hostname')
                    if hostname is None:
                        continue

                    if name == hostname:

                        cellinfo = None
                        if svcdef.get('online') is not None:
                            ok, retn = await prox.callAhaSvcApi(name, todo, timeout=opts.timeout)
                            if ok:
                                cellinfo = retn

                        runs[svcdef.get('run')] = svcdef
                        clusters[iden].append((svcdef, cellinfo))

                    else:
                        virtuals[iden].append(svcdef)

                for iden, svcdefs in clusters.items():

                    virts = virtuals.get(iden)
                    if not virts and len(svcdefs) == 1:
                        continue

                    outp.printf(f'Service Cluster: {iden}')

                    if virts:
                        virts.sort(key=lambda x: x['name'])
                        outp.printf('')
                        outp.printf(f'  {"Virtual":<32} {"Name":<32}')

                        for virtsvc in virts:

                            virtrun = virtsvc.get('run')
                            virtname = virtsvc.get('name')
                            realname = '<unknown>'

                            svcdef = runs.get(virtrun)
                            if svcdef is not None:
                                realname = svcdef.get('name')

                            outp.printf(f'  {virtname:<32} {realname:<32}')

                    outp.printf('')
                    outp.printf(f'  {"Name":<32} {"Leader":<6} {"Ready":<5} {"Nexus":<11} {"Version":<12} {"Synapse":<12}')

                    svcdefs.sort(key=lambda x: x[0]['name'])

                    for (svcdef, cellinfo) in svcdefs:

                        name = svcdef.get('name')
                        ready = str(svcdef.get('ready')).lower()

                        isleader = ''
                        synvers = '<offline>'
                        cellvers = '<offline>'
                        nexsindx = '<offline>'

                        if cellinfo is not None:
                            isleader = str(not cellinfo['cell'].get('uplink')).lower()
                            synvers = '.'.join(str(v) for v in cellinfo['synapse'].get('version'))
                            cellvers = '.'.join(str(v) for v in cellinfo['cell'].get('version'))
                            nexsindx = str(cellinfo['cell'].get('nexsindx'))

                        outp.printf(f'  {name:<32} {isleader:<6} {ready:<5} {nexsindx:<11} {cellvers:<12} {synvers:<12}')

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

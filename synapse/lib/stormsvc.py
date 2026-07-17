import logging

logger = logging.getLogger(__name__)

stormcmds = (
    {
        'name': 'service.add',
        'descr': 'Add a storm service to the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name of the service.'}),
            ('url', {'help': 'The telepath URL for the remote service.'}),
        ),
        'cmdconf': {},
        'storm': '''
            $sdef = $lib.service.add($cmdopts.name, $cmdopts.url)
            $lib.print(`added {$sdef.iden} ({$sdef.name}): {$sdef.url}`)
        ''',
    },
    {
        'name': 'service.del',
        'descr': 'Remove a storm service from the cortex.',
        'cmdargs': (
            ('iden', {'help': 'The service identifier or prefix.'}),
        ),
        'cmdconf': {},
        'storm': '''
            $svcs = ()

            for $sdef in $lib.service.list() {
                if $sdef.iden.startswith($cmdopts.iden) {
                    $svcs.append($sdef)
                }
            }

            $count = $svcs.size()

            if $( $count = 1 ) {
                $sdef = $svcs.index(0)
                $lib.service.del($sdef.iden)
                $lib.print(`removed {$sdef.iden} ({$sdef.name}): {$sdef.url}`)
            } elif $( $count = 0 ) {
                $lib.print(`No service found by iden: {$cmdopts.iden}`)
            } else {
                $lib.print(`Multiple matches found for {$cmdopts.iden}.  Aborting delete.`)
            }
        ''',
    },
    {
        'name': 'service.list',
        'descr': 'List the storm services configured in the cortex.',
        'cmdconf': {},
        'storm': '''
            $lib.print("")
            $lib.print("Storm service list (iden, ready, name, service name, service version, url):")
            $count = $(0)
            for $sdef in $lib.service.list() {
                $url = $sdef.url
                $iden = $sdef.iden
                $name = $sdef.name
                $ready = $sdef.ready
                $sname = $sdef.svcname
                if $sname {} else { $sname = 'Unknown' }
                $svers = $sdef.svcvers
                if (not $svers) {
                    $svers = 'Unknown'
                }
                $lib.print(`    {$iden} {$ready} ({$name}) ({$sname} @ {$svers}): {$url}`)
                $count = $( $count + 1 )
            }
            $lib.print("")
            $lib.print(`{$count} services`)
        ''',
    }
)

class StormSvc:
    '''
    The StormSvc mixin class used to make a remote storm service with commands.
    '''

    _storm_svc_name = 'noname'
    _storm_svc_vers = '0.0.1'
    _storm_svc_evts = {}  # type: ignore
    _storm_svc_pkgs = ()  # type: ignore

    async def getStormSvcInfo(self):
        # Users must specify the service name
        assert self._storm_svc_name != 'noname'
        return {
            'name': self._storm_svc_name,
            'vers': self._storm_svc_vers,
            'evts': self._storm_svc_evts,
            'pkgs': await self.getStormSvcPkgs(),
        }

    async def getStormSvcPkgs(self):
        return self._storm_svc_pkgs

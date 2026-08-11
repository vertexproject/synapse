import logging

import synapse.exc as s_exc

import synapse.lib.const as s_const

logger = logging.getLogger(__name__)

stormcmds = (
    {
        'name': 'service.add',
        'desc': 'Add a storm service to the cortex.',
        'cmdargs': (
            ('name', {'help': 'The cell type name of the service.'}),
            ('url', {'help': 'The telepath URL for the remote service.'}),
        ),
        'cmdconf': {},
        'storm': '''
            $sdef = $lib.service.add($cmdopts.name, $cmdopts.url)
            $lib.print(`added {$sdef.name}: {$sdef.url}`)
        ''',
    },
    {
        'name': 'service.del',
        'desc': 'Remove a storm service from the cortex.',
        'cmdargs': (
            ('name', {'help': 'The cell type name of the service.'}),
        ),
        'cmdconf': {},
        'storm': '''
            $svcs = ()

            for $sdef in $lib.service.list() {
                if ($sdef.name = $cmdopts.name) {
                    $svcs.append($sdef)
                }
            }

            if $( $svcs.size() = 1 ) {
                $sdef = $svcs.index(0)
                $lib.service.del($sdef.name)
                $lib.print(`removed {$sdef.name}: {$sdef.url}`)
            } else {
                $lib.print(`No service found by name: {$cmdopts.name}`)
            }
        ''',
    },
    {
        'name': 'service.list',
        'desc': 'List the storm services configured in the cortex.',
        'cmdconf': {},
        'storm': '''
            $lib.print("")
            $lib.print("Storm service list (ready, name, service version, url):")
            $count = $(0)
            for $sdef in $lib.service.list() {
                $url = $sdef.url
                $name = $sdef.name
                $ready = $sdef.ready
                $svers = $sdef.svcvers
                if (not $svers) {
                    $svers = 'Unknown'
                }
                $lib.print(`    {$ready} ({$name} @ {$svers}): {$url}`)
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

    A storm service delivers exactly one storm package. The cortex identifies a
    service by its cell type ( which is unique for a deployment ), so a package
    which needs to call back into the service that delivered it does so by that
    name rather than by a generated iden.
    '''

    # The storm package delivered by this service.
    _storm_svc_pkg = None  # type: ignore

    # Maps the package relative path of each file declared by our package to the
    # path it may be read from. Build with s_genpkg.getPkgProtoFiles() over the
    # package proto. Serving by path rather than sha256 means the mapping is stable
    # no matter how the file contents change.
    _storm_svc_pkgfiles = {}  # type: ignore

    async def getStormSvcPkg(self):
        return self._storm_svc_pkg

    async def getStormSvcPkgFile(self, path):
        '''
        Yield the bytes of a file declared by our storm package.

        Args:
            path (str): The path of the file, relative to the package files directory.

        Yields:
            bytes: Chunks of the file contents.
        '''
        fullpath = self._storm_svc_pkgfiles.get(path)
        if fullpath is None:
            mesg = f'Storm package has no file with path {path}.'
            raise s_exc.NoSuchFile(mesg=mesg, path=path)

        with open(fullpath, 'rb') as fd:
            while (byts := fd.read(s_const.mebibyte)):
                yield byts

import asyncio
import logging

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.stormtypes as s_stormtypes

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
            $lib.print("added {iden} ({name}): {url}", iden=$sdef.iden, name=$sdef.name, url=$sdef.url)
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

            $count = $svcs.length()

            if $( $count = 1 ) {
                $sdef = $svcs.index(0)
                $lib.service.del($sdef.iden)
                $lib.print("removed {iden} ({name}): {url}", iden=$sdef.iden, name=$sdef.name, url=$sdef.url)
            } elif $( $count = 0 ) {
                $lib.print("No service found by iden: {iden}", iden=$cmdopts.iden)
            } else {
                $lib.print('Multiple matches found for {iden}.  Aborting delete.', iden=$cmdopts.iden)
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
                if $svers {
                    $svers = $lib.str.join('.', $svers)
                } else {
                    $svers = 'Unknown'
                }
                $mesg="    {iden} {ready} ({name}) ({sname} @ {svers}): {url}"
                $lib.print(mesg=$mesg, iden=$iden, ready=$ready, name=$name, sname=$sname, svers=$svers, url=$url)
                $count = $( $count + 1 )
            }
            $lib.print("")
            $lib.print("{count} services", count=$count)
        ''',
    }
)

class StormSvc:
    '''
    The StormSvc mixin class used to make a remote storm service with commands.
    '''

    _storm_svc_name = 'noname'
    _storm_svc_vers = (0, 0, 1)
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

class StormSvcClient(s_base.Base):
    '''
    A StormService is a wrapper for a telepath proxy to a service
    accessible from the storm runtime.
    '''
    async def __anit__(self, core, sdef):

        await s_base.Base.__anit__(self)

        self.core = core
        self.sdef = sdef

        self.iden = sdef.get('iden')
        self.name = sdef.get('name')  # Local name for the cortex
        self.svcname = ''  # remote name from the service
        self.svcvers = ''  # remove version from the service

        # service info from the server...
        self.info = None

        url = self.sdef.get('url')

        self.ready = asyncio.Event()

        self.proxy = await s_telepath.Client.anit(url, onlink=self._onTeleLink)
        self.onfini(self.proxy.fini)

    async def _runSvcInit(self):
        # Set the latest reference for this object to the remote svcname
        self.core.svcsbysvcname.pop(self.svcname, None)
        self.svcname = self.info['name']
        self.svcvers = self.info['vers']
        self.core.svcsbysvcname[self.svcname] = self

        try:
            await self.core._delStormSvcPkgs(self.iden)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception:
            logger.exception(f'_delStormSvcPkgs failed for service {self.name} ({self.iden})')

        # Register new packages
        for pdef in self.info.get('pkgs', ()):

            try:
                # push the svciden in the package metadata for later reference.
                pdef['svciden'] = self.iden
                await self.core._normStormPkg(pdef)
                await self.core._addStormPkg(pdef)

            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise

            except Exception:
                name = pdef.get('name')
                logger.exception(f'addStormPkg ({name}) failed for service {self.name} ({self.iden})')

        # Set events and fire as needed
        evts = self.info.get('evts')
        try:
            if evts is not None:
                self.sdef = await self.core.setStormSvcEvents(self.iden, evts)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception:
            logger.exception(f'setStormSvcEvents failed for service {self.name} ({self.iden})')

        try:
            if self.core.isactive:
                await self.core._runStormSvcAdd(self.iden)

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception:
            logger.exception(f'service.add storm hook failed for service {self.name} ({self.iden})')

    async def _onTeleLink(self, proxy):

        clss = proxy._getClasses()

        names = [c.rsplit('.', 1)[-1] for c in clss]

        if 'StormSvc' in names:
            self.info = await proxy.getStormSvcInfo()
            await self._runSvcInit()

        async def unready():
            self.ready.clear()
            await self.core.fire("stormsvc:client:unready", iden=self.iden)

        proxy.onfini(unready)

        self.ready.set()

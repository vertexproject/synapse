import synapse.lib.cell as s_cell
import synapse.lib.stormsvc as s_stormsvc

class TestsvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = {
        'name': 'testsvc',
        'version': '0.0.1',
        'onload': '''
            $time = $lib.globals.onload_sleep
            if ($time = null) { $time = (0) }
            $lib.time.sleep($time)
            $lib.globals.testsvc = testsvc-done
        ''',
        'commands': (
            {
                'name': 'testsvc.test',
                'storm': '''
                    $lib.print($lib.service.get(testsvc).test())
                    $lib.print($lib.globals.testsvc)
                ''',
            },
        )
    }

    async def test(self):
        return await self.cell.test()

class Testsvc(s_cell.Cell):

    celltype = 'testsvc'
    cellapi = TestsvcApi

    confdefs = {
        'secret': {'type': 'string'},
    }

    async def __anit__(self, dirn, conf=None):
        await s_cell.Cell.__anit__(self, dirn, conf=conf)
        self.secret = self.conf.req('secret')

    async def test(self):
        return self.secret

class AhaTestsvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = {
        'name': 'ahatestsvc',
        'version': '0.0.1',
        'commands': (
            {
                'name': 'ahatestsvc.test',
                'storm': '''
                    $lib.print($lib.service.get(ahatestsvc).test())
                ''',
            },
        )
    }

    async def test(self):
        return await self.cell.test()

class AhaTestsvc(s_cell.Cell):
    '''
    A --load-svc ctor that requires AHA to boot, like a real power-up
    resolving a peer by cell type ( e.g. FileParser resolving aha://axon... )
    -- used to exercise MdStorm._startStormSvc's AHA-join path.
    '''

    celltype = 'ahatestsvc'
    cellapi = AhaTestsvcApi

    async def initServiceRuntime(self):
        self._reqAhaServers()
        return await super().initServiceRuntime()

    async def test(self):
        return 'ahatestsvc-ok'

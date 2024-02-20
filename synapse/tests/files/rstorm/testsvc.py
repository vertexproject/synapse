import synapse.lib.cell as s_cell
import synapse.lib.stormsvc as s_stormsvc

class TestsvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_name = 'testsvc'
    _storm_svc_vers = (0, 0, 1)
    _storm_svc_pkgs = (
        {
            'name': 'testsvc',
            'version': (0, 0, 1),
            'commands': (
                {
                    'name': 'testsvc.test',
                    'storm': '$lib.print($lib.service.get($cmdconf.svciden).test())',
                },
            )
        },
    )

    async def test(self):
        return await self.cell.test()

class Testsvc(s_cell.Cell):

    cellapi = TestsvcApi

    confdefs = {
        'secret': {'type': 'string'},
    }

    async def __anit__(self, dirn, conf):
        await s_cell.Cell.__anit__(self, dirn, conf=conf)
        self.secret = self.conf.reqConfValu('secret')

    async def test(self):
        return self.secret

import os
import copy
import json
import contextlib

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.hive as s_hive
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

import synapse.tools.migrate_020 as s_migr

TESTDIR = os.path.split(__file__)[0]
ASSETDIR = os.path.join(TESTDIR, 'files', 'migration')

def getAssetPath(*paths):
    fp = os.path.join(ASSETDIR, *paths)
    assert os.path.isfile(fp)
    return fp


def getAssetBytes(*paths):
    fp = getAssetPath(*paths)
    with open(fp, 'rb') as f:
        byts = f.read()
    return byts


def getAssetJson(*paths):
    byts = getAssetBytes(*paths)
    obj = json.loads(byts.decode())
    return obj

class MigrationCore(s_base.Base):

    async def __anit__(self, dirn):
        await s_base.Base.__anit__(self)
        self.dirn = dirn

    async def createCore(self):
        # raw test rows
        testbyts = getAssetBytes('migrrows.txt')
        testrows = testbyts.split(b'000000')

        # initialize dirn
        iden = s_common.guid()
        pathlyr = s_common.gendir(self.dirn, 'layers', iden, 'layer.lmdb')
        pathcell = s_common.gendir(self.dirn, 'slabs', 'cell.lmdb')

        path = s_common.genpath(self.dirn, 'cell.guid')
        with open(path, 'w') as fd:
            fd.write(s_common.guid())

        # initialize hive
        hiveslab = await s_lmdbslab.Slab.anit(pathcell, readonly=False)
        hivedb = hiveslab.initdb('hive')
        hive = await s_hive.SlabHive.anit(hiveslab, db=hivedb)
        self.onfini(hiveslab.fini)
        self.onfini(hive.fini)

        # add base layer to hive
        hlyrs = await hive.open(('cortex', 'layers', iden))
        layrinfo = await hlyrs.dict()
        await layrinfo.set('type', 'lmdb')
        await layrinfo.set('owner', 'root')
        await layrinfo.set('name', '??')

        # default view
        viden = s_common.guid()
        hcellinf = await hive.open(('cellinfo', ))
        cellinf = await hcellinf.dict()
        await cellinf.set('defaultview', viden)

        hviews = await hive.open(('cortex', 'views', viden))
        viewinfo = await hviews.dict()
        await viewinfo.set('owner', 'root')
        await viewinfo.set('name', '??')
        await viewinfo.set('layers', [iden])

        # hive default user
        husr = await hive.open(('auth', 'users'))
        usrinfo = await husr.dict()
        await usrinfo.set(s_common.guid(), 'root')

        # add partial extended models
        extprops = await (await hive.open(('cortex', 'model', 'props'))).dict()
        await extprops.set(s_common.guid(), ('inet:ipv4', '_rdxp', ('int', {}), {}))  # not adding "_rdxpz"

        extunivs = await (await hive.open(('cortex', 'model', 'univs'))).dict()
        await extunivs.set(s_common.guid(), ('_rdxu', ('str', {'lower': True}), {}))

        exttagprops = await (await hive.open(('cortex', 'model', 'tagprops'))).dict()
        await exttagprops.set(s_common.guid(), ('score', ('int', {}), {}))  # not adding "nah"

        # initialize bybuid db
        slab = await s_lmdbslab.Slab.anit(pathlyr, map_async=True, readonly=False)
        bybuid = slab.initdb('bybuid')
        self.onfini(slab.fini)

        # add data (rows are sequential as keys/val)
        for i in range(0, len(testrows), 2):
            slab.put(testrows[i], testrows[i + 1], db=bybuid)

        rrows = []
        for lkey, lval in slab.scanByFull(db=bybuid):
            rrows.append((lkey, lval))

        assert len(rrows) == len(testrows) / 2

        await self.fini()

        return iden

class MigrationTest(s_t_utils.SynTest):

    async def _convertJsonPode(self, pode):
        '''
        Convert json lists to tuples for eq testing.
        '''
        # convert if comp form
        if isinstance(pode[0][1], list):
            pode[0][1][0] = tuple(pode[0][1][0])
            pode[0][1][1] = tuple(pode[0][1][1])
            pode[0][1] = tuple(pode[0][1])

        pode[0] = tuple(pode[0])

        for topk, topv in pode[1].items():
            if isinstance(topv, dict):
                for botk, botv in pode[1][topk].items():
                    if isinstance(botv, list):
                        pode[1][topk][botk] = tuple(botv)

            # comp form repr
            elif isinstance(topv, list):
                pode[1][topk][0] = tuple(pode[1][topk][0])
                pode[1][topk][1] = tuple(pode[1][topk][1])
                pode[1][topk] = tuple(pode[1][topk])

        return pode

    @contextlib.asynccontextmanager
    async def _getTestMigrCore(self, conf):
        # create migration core
        migrcore = await MigrationCore.anit(conf['dirn'])
        iden = await migrcore.createCore()

        # initialize migration tool
        tconf = copy.deepcopy(conf)

        async with await s_migr.Migrator.anit(tconf) as migr:
            yield iden, migr

    @contextlib.asynccontextmanager
    async def _getTestCore(self, dirn):
        async with self.getTestCore(dirn=dirn) as core:
            await core.addFormProp('inet:ipv4', '_rdxp', ('int', {}), {})
            await core.addFormProp('inet:ipv4', '_rdxpz', ('int', {}), {})
            await core.addUnivProp('_rdxu', ('str', {'lower': True}), {})
            await core.addTagProp('score', ('int', {}), {})
            await core.addTagProp('nah', ('int', {}), {})

            yield core

    async def test_migration(self):

        with self.getTestDir() as dirn:
            conf = {
                'dirn': dirn,
                'migrops': [
                    'dmodel',
                    'hiveauth',
                    'hivestor',
                    'hivelyr',
                    'nodes',
                    # 'nodedata',
                    'hive',
                ],
            }

            async with self._getTestMigrCore(conf) as (iden, migr):
                await migr.migrate()

                stats = await migr._migrlogGet('nodes', 'stat', f'{iden}:form')
                for stat in stats:
                    skey = stat['key']
                    sval = stat['val']  # (src_cnt, dest_cnt)

                    if skey.endswith('inet:ipv4'):
                        self.eq((2, 1), sval)  # expecting one ipv4 to fail due to missing props currently
                    elif skey.endswith('syn:tag'):
                        self.eq((3, 3), sval)
                    else:
                        self.eq((1, 1), sval)

                await migr.fini()

            # startup 0.2.0 core
            async with self._getTestCore(dirn=dirn) as core:
                testpodes = getAssetJson('migrpodes.json')

                tpode = await self._convertJsonPode(testpodes[0])
                nodes = await core.nodes('inet:ipv4=1.2.3.4')
                self.len(1, nodes)
                pode = nodes[0].pack(dorepr=True)
                self.eq(pode, tpode)

                # node adds are currently atomic, so this entry should not exist
                nodes = await core.nodes('inet:ipv4=5.6.7.8')
                self.len(0, nodes)

                tpode = await self._convertJsonPode(testpodes[2])
                nodes = await core.nodes('file:bytes=c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2')
                self.len(1, nodes)
                pode = nodes[0].pack(dorepr=True)
                self.eq(pode, tpode)

                tpode = await self._convertJsonPode(testpodes[3])
                scmd = (
                    f'edge:has=((inet:ipv4, 1.2.3.4),'
                    f'(file:bytes, c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2))'
                )
                nodes = await core.nodes(scmd)
                self.len(1, nodes)
                pode = nodes[0].pack(dorepr=True)
                self.eq(pode, tpode)

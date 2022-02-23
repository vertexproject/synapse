import os
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.tests.utils as s_tests
import synapse.lib.modelrev as s_modelrev

def nope(*args, **kwargs):
    raise Exception('nope was called')

class ModelRevTest(s_tests.SynTest):

    async def test_cortex_modelrev_init(self):

        with self.getTestDir(mirror='testcore') as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:
                layr = core.getLayer()
                self.true(layr.fresh)
                self.eq(s_modelrev.maxvers, await layr.getModelVers())

            # no longer "fresh", but lets mark a layer as read only
            # and test the bail condition for layers which we cant update
            async with await s_cortex.Cortex.anit(dirn) as core:

                layr = core.getLayer()
                layr.canrev = False

                mrev = s_modelrev.ModelRev(core)

                mrev.revs = mrev.revs + (((9999, 9999, 9999), nope),)

                with self.raises(s_exc.CantRevLayer):
                    await mrev.revCoreLayers()

            # no longer "fresh"
            async with await s_cortex.Cortex.anit(dirn) as core:

                layr = core.getLayer()
                self.false(layr.fresh)

                self.eq(s_modelrev.maxvers, await layr.getModelVers())

                mrev = s_modelrev.ModelRev(core)

                layr.woot = False

                async def woot(layers):
                    layr.woot = True

                mrev.revs = mrev.revs + (((9999, 9999, 9999), woot),)

                await mrev.revCoreLayers()

                self.true(layr.woot)
                self.eq((9999, 9999, 9999), await layr.getModelVers())

    async def test_modelrev_2_0_1(self):
        async with self.getRegrCore('model-2.0.1') as core:

            nodes = await core.nodes('ou:org=b084f448ee7f95a7e0bc1fd7d3d7fd3b')
            self.len(1, nodes)
            self.len(3, nodes[0].get('industries'))

            nodes = await core.nodes('ou:org=57c2dd4feee21204b1a989b9a796a89d')
            self.len(1, nodes)
            self.len(1, nodes[0].get('industries'))

    async def test_modelrev_0_2_2(self):
        async with self.getRegrCore('model-0.2.2') as core:
            nodes = await core.nodes('inet:web:acct:signup:client:ipv6="::ffff:1.2.3.4"')
            self.len(2001, nodes)

    async def test_modelrev_0_2_3(self):

        async with self.getRegrCore('model-0.2.3') as core:

            nodes = await core.nodes('it:exec:proc:cmd=rar.exe')
            self.len(2001, nodes)

            nodes = await core.nodes('it:cmd')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:cmd', 'rar.exe'))

    async def test_modelrev_0_2_4(self):
        async with self.getRegrCore('model-0.2.4') as core:

            nodes = await core.nodes('ps:person=1828dca605977725540bb74f728d9d81')
            self.len(1, nodes)
            self.len(1, nodes[0].get('names'))

            nodes = await core.nodes('ps:person=d26a988f732371e51e36fea0f16ff382')
            self.len(1, nodes)
            self.len(3, nodes[0].get('names'))

            nodes = await core.nodes('ps:person=c92e49791022c88396fa69d9f94281cb')
            self.len(1, nodes)
            self.len(3, nodes[0].get('names'))

            nodes = await core.nodes('ps:person:name=coverage')
            self.len(1003, nodes)
            for node in nodes:
                self.len(1, nodes[0].get('names'))

    async def test_modelrev_0_2_6(self):
        async with self.getRegrCore('model-0.2.6') as core:

            acct = '90b3d80f8bdf9e33b4aeb46c720d3289'
            nodes = await core.nodes(f'it:account={acct}')
            self.len(1, nodes)
            self.len(2, nodes[0].get('groups'))

            g00 = 'd0d235109162501db9d4014a4c2cc4d9'
            g01 = 'bf1999e8c45523bc64803e28b19a34c6'
            nodes = await core.nodes(f'it:account={acct} [:groups=({g00}, {g01}, {g00})]')
            self.len(1, nodes)
            self.len(2, nodes[0].get('groups'))

            url0 = "https://charlie.com/woot"
            url1 = "https://bravo.com/woot"
            url2 = "https://delta.com/woot"
            url3 = "https://alpha.com/woot"

            # created via: f'[it:sec:cve=CVE-2013-9999 :desc="some words" :references=({url0}, {url1}, {url2}, {url3})]'
            nodes = await core.nodes(f'it:sec:cve=CVE-2013-9999')
            self.eq(nodes[0].ndef[1], 'cve-2013-9999')
            self.eq(nodes[0].get('desc'), 'some words')
            self.eq(nodes[0].get('references'), (url3, url1, url0, url2))

    async def test_modelrev_0_2_7(self):

        async with self.getRegrCore('model-0.2.7') as core:

            nodes = await core.nodes('_test:huge=0.000000000000009')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], '0.000000000000009')

            nodes = await core.nodes("crypto:smart:token=(ad17516393ea1857ea660c290112bcca, '0.000000000000002')")
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1][1], '0.000000000000002')
            self.eq(nodes[0].props["tokenid"], '0.000000000000002')

            nodes = await core.nodes("crypto:smart:token:tokenid='0.000000000000002'")
            self.len(1, nodes)

            nodes = await core.nodes('crypto:smart:token:nft:url=http://layer.com')
            self.len(0, nodes)

            opts = {'view': '9477410524e02fcd91608decd6314574'}

            nodes = await core.nodes('crypto:smart:token:nft:url=http://layer.com', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].props["tokenid"], '0.000000000000002')

            nodes = await core.nodes("crypto:smart:token -(hnum)> *")
            self.len(1, nodes)

            nodes = await core.nodes("crypto:smart:token <(*)- *")
            self.len(1, nodes)

            nodes = await core.nodes('_test:huge <(layer2)- *', opts=opts)
            self.len(10, nodes)

            nodes = await core.nodes('_test:huge -(layer2)> *', opts=opts)
            self.len(12, nodes)

            nodes = await core.nodes('inet:fqdn=huge.com <(layer2)- *', opts=opts)
            self.len(3, nodes)

            nodes = await core.nodes('yield $lib.lift.byNodeData(layer2)', opts=opts)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('_test:huge', '0.000000000000009'))
            self.eq(nodes[1].ndef, ('crypto:smart:token',
                                   ('ad17516393ea1857ea660c290112bcca', '0.000000000000002')))
            self.eq(nodes[1].props["tokenid"], '0.000000000000002')

            nodes = await core.nodes('yield $lib.lift.byNodeData(layer2)')
            self.len(0, nodes)

            nodes = await core.nodes('yield $lib.lift.byNodeData(compdata)')
            self.len(2, nodes)

            nodes = await core.nodes('''
                _test:hugearraycomp=(
                    (bd7f5abb84db51d9845b238f62a6684d, 0.000000000000001),
                    (20a84f63e2820ff8b2caed85ba096360, 0.000000000000006)
                )
            ''')
            self.len(1, nodes)

            nodes = await core.nodes('''
                _test:hugearraycomp=(
                    ('11b51985e9e5a3eadcb9ddeb3e05f4b7', 0.00000000000001),
                    ('0c640aab86c6e1ab5283b9410e54019a', 0.00000000000006)
                )
            ''')
            self.len(1, nodes)

            nodes = await core.nodes("crypto:smart:token=('36758b150b708675b2fec5a7768bcc25', '70E-15')")
            self.len(1, nodes)
            self.eq(nodes[0].props["tokenid"], '0.00000000000007')

            nodes = await core.nodes("crypto:smart:token=('36758b150b708675b2fec5a7768bcc25', '0.00000000000007')")
            self.len(1, nodes)

            nodes = await core.nodes("crypto:smart:token=('36758b150b708675b2fec5a7768bcc25', '0.000000000000070')")
            self.len(1, nodes)

            nodes = await core.nodes("edge:has -> _test:huge")
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('_test:huge', '0.00000000000009'))
            self.eq(nodes[1].ndef, ('_test:huge', '0.000000000000009'))

            hugearray = ('_test:hugearraycomp',
                            (('bd7f5abb84db51d9845b238f62a6684d', '0.000000000000001'),
                             ('20a84f63e2820ff8b2caed85ba096360', '0.000000000000006')))

            nodes = await core.nodes("econ:acquired")
            self.len(4, nodes)
            self.eq(nodes[0].props['item'], ('_test:huge', '0.00000000000001'))
            self.eq(nodes[2].props['item'], hugearray)

            nodes = await core.nodes("._huge:univarraycomp")
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1][0], ('bd7f5abb84db51d9845b238f62a6684d', '0.000000000000001'))
            self.eq(nodes[0].ndef[1][1], ('20a84f63e2820ff8b2caed85ba096360', '0.000000000000006'))

            nodes = await core.nodes("inet:web:chprofile")
            self.len(1, nodes)
            self.eq(nodes[0].props['pv'], ('crypto:smart:token:tokenid', '0.00000000000004'))

            nodes = await core.nodes("_test:hugerange")
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('_test:hugerange', ('0.00000000000005', '0.00000000000008')))

            nodes = await core.nodes('inet:fqdn:_huge')
            self.len(1, nodes)
            self.eq(nodes[0].props['_huge'], '0.000000000000009')

            nodes = await core.nodes('crypto:currency:transaction:value=0.000000000000003')
            self.len(1, nodes)
            self.eq(nodes[0].props['value'], '0.000000000000003')

            nodes = await core.nodes("inet:fqdn:_huge:array*[=0.000000000000001]")
            self.len(1, nodes)
            self.eq(nodes[0].props['_huge:array'], ('0.000000000000001', '0.000000000000002'))

            nodes = await core.nodes("#test:cool:huge=0.000000000000005", opts=opts)
            self.len(3, nodes)

            nodes = await core.nodes("#test:cool:huge=0.000000000000005")
            self.len(2, nodes)

            nodes = await core.nodes("#test:cool:comp")
            self.len(2, nodes)
            self.eq(nodes[0].tagprops['test']['cool:comp'],
                    ('3ae73f6cb7befaccb5ed79ca91e66bb0', '0.000000000000012'))
            self.eq(nodes[1].tagprops['test']['cool:comp'],
                    ('e7dd87edb04dc9d541ede108c8887b99', '0.000000000000012'))

            nodes = await core.nodes('crypto:currency:transaction:value>=0.000000000000001')
            self.len(3, nodes)

            nodes = await core.nodes('crypto:currency:transaction:value>0.00000000000000000001')
            self.len(5, nodes)

            nodes = await core.nodes('crypto:currency:transaction:value<=0.00000000000000000002')
            self.len(3, nodes)

            nodes = await core.nodes('crypto:currency:transaction:value<0.00000000000000000002')
            self.len(2, nodes)

            nodes = await core.nodes('crypto:currency:transaction:value=0')
            self.len(1, nodes)

            q = '''
            crypto:currency:transaction:value*range=(
            0.00000000000000000002, 0.00000000000000000003
            )'''
            nodes = await core.nodes(q)
            self.len(2, nodes)

            nodes = await core.nodes('_test:huge=90E-15')
            self.len(1, nodes)

            self.len(1006, nodes[0].props)
            self.len(1005, nodes[0].tags)
            self.len(1005, nodes[0].tagprops)

            self.eq(1005, await core.callStorm('_test:huge=90E-15 return($node.data.list().size())'))

            layers = list(core.layers.values())

            errors = [e async for e in layers[0].verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'SpurTagPropKeyForIndex')
            self.eq(errors[1][0], 'SpurTagPropKeyForIndex')

            errors = [e async for e in layers[1].verify()]
            self.len(2, errors)
            self.eq(errors[0][0], 'NoPropForTagPropIndex')
            self.eq(errors[1][0], 'NoPropForTagPropIndex')

    async def test_modelrev_0_2_6_mirror(self):

        regr = os.getenv('SYN_REGRESSION_REPO')
        if regr is None:
            raise unittest.SkipTest('SYN_REGRESSION_REPO is not set')

        regr = s_common.genpath(regr)

        if not os.path.isdir(regr):
            raise Exception('SYN_REGRESSION_REPO is not a dir')

        dirn = os.path.join(regr, 'cortexes', 'model-0.2.7')

        with self.getTestDir(copyfrom=dirn) as regrdir00:

            with self.getTestDir(copyfrom=dirn) as regrdir01:

                conf00 = {'nexslog:en': True}

                async with await s_cortex.Cortex.anit(regrdir00, conf=conf00) as core00:

                    self.eq(core00.model.vers, (0, 2, 8))

                    conf01 = {'nexslog:en': True, 'mirror': core00.getLocalUrl()}

                async with await s_cortex.Cortex.anit(regrdir01, conf=conf01) as core01:

                    self.eq(core01.model.vers, (0, 2, 6))

                    nodes = await core01.nodes('crypto:currency:transaction:value>=0.000000000000001')
                    self.len(7, nodes)

                    nodes = await core01.nodes('crypto:currency:transaction:value>0.00000000000000000001')
                    self.len(0, nodes)

                    nodes = await core01.nodes('crypto:currency:transaction:value<=0.00000000000000000002')
                    self.len(7, nodes)

                    nodes = await core01.nodes('crypto:currency:transaction:value<0.00000000000000000002')
                    self.len(0, nodes)

                    nodes = await core01.nodes('crypto:currency:transaction:value=0')
                    self.len(7, nodes)

                    with self.raises(s_exc.BadTypeValu):
                        nodes = await core01.nodes('crypto:currency:transaction:value=foo')

                    with self.raises(s_exc.BadTypeValu):
                        nodes = await core01.nodes('crypto:currency:transaction:value=170141183460469231731688')

                    with self.raises(s_exc.BadTypeValu):
                        nodes = await core01.nodes('crypto:currency:transaction:value=-170141183460469231731688')

                async with await s_cortex.Cortex.anit(regrdir00, conf=conf00) as core00:
                    async with await s_cortex.Cortex.anit(regrdir01, conf=conf01) as core01:

                        await core01.sync()

                        self.eq(core01.model.vers, (0, 2, 8))

                        nodes = await core01.nodes('crypto:currency:transaction:value>=0.000000000000001')
                        self.len(3, nodes)

                        nodes = await core01.nodes('crypto:currency:transaction:value>0.00000000000000000001')
                        self.len(5, nodes)

                        nodes = await core01.nodes('crypto:currency:transaction:value<=0.00000000000000000002')
                        self.len(3, nodes)

                        nodes = await core01.nodes('crypto:currency:transaction:value<0.00000000000000000002')
                        self.len(2, nodes)

                        nodes = await core01.nodes('crypto:currency:transaction:value=0')
                        self.len(1, nodes)

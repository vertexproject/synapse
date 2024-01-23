import synapse.exc as s_exc

import synapse.lib.chop as s_chop
import synapse.lib.modelrev as s_modelrev

import synapse.tests.utils as s_tests


def nope(*args, **kwargs):
    raise Exception('nope was called')

class ModelRevTest(s_tests.SynTest):

    async def test_cortex_modelrev_init(self):

        with self.getTestDir(mirror='testcore') as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                layr = core.getLayer()
                self.true(layr.fresh)
                self.eq(s_modelrev.maxvers, await layr.getModelVers())

            # no longer "fresh", but lets mark a layer as read only
            # and test the bail condition for layers which we cant update
            async with self.getTestCore(dirn=dirn) as core:

                layr = core.getLayer()
                layr.canrev = False

                mrev = s_modelrev.ModelRev(core)

                mrev.revs = mrev.revs + (((9999, 9999, 9999), nope),)

                with self.raises(s_exc.CantRevLayer):
                    await mrev.revCoreLayers()

            # no longer "fresh"
            async with self.getTestCore(dirn=dirn) as core:

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

    async def test_modelrev_0_2_7_mirror(self):

        vers = '2.85.1-hugenum-indx'

        with self.getRegrDir('cortexes', vers) as regrdir00:

            with self.getRegrDir('cortexes', vers) as regrdir01:

                conf00 = {'nexslog:en': True}

                async with self.getTestCore(dirn=regrdir00, conf=conf00) as core00:

                    self.true(await core00.getLayer().getModelVers() >= (0, 2, 7))

                    conf01 = {'nexslog:en': True, 'mirror': core00.getLocalUrl()}

                async with self.getTestCore(dirn=regrdir01, conf=conf01) as core01:

                    self.eq(await core01.getLayer().getModelVers(), (0, 2, 6))

                    nodes = await core01.nodes('inet:fqdn=baz.com')
                    self.len(1, nodes)
                    node = nodes[0]
                    self.eq(node.props.get('_huge'), '10E-21')
                    self.eq(node.props.get('._univhuge'), '10E-21')
                    self.eq(node.props.get('._hugearray'), ('3.45', '10E-21'))
                    self.eq(node.props.get('._hugearray'), ('3.45', '10E-21'))

                async with self.getTestCore(dirn=regrdir00, conf=conf00) as core00:
                    async with self.getTestCore(dirn=regrdir01, conf=conf01) as core01:

                        await core01.sync()

                        self.true(await core01.getLayer().getModelVers() >= (0, 2, 7))

                        nodes = await core01.nodes('inet:fqdn=baz.com')
                        self.len(1, nodes)
                        node = nodes[0]
                        self.eq(node.props.get('_huge'), '0.00000000000000000001')
                        self.eq(node.props.get('._univhuge'), '0.00000000000000000001')
                        self.eq(node.props.get('._hugearray'), ('3.45', '0.00000000000000000001'))
                        self.eq(node.props.get('._hugearray'), ('3.45', '0.00000000000000000001'))

    async def test_modelrev_0_2_8(self):
        # Test geo:place:name re-norming
        # Test crypto:currency:block:hash re-norming
        # Test crypto:currency:transaction:hash re-norming
        async with self.getRegrCore('2.87.0-geo-crypto') as core:

            # Layer migrations
            nodes = await core.nodes('geo:place:name="big hollywood sign"')
            self.len(1, nodes)

            nodes = await core.nodes('crypto:currency:block:hash')
            self.len(1, nodes)
            valu = nodes[0].get('hash')  # type: str
            self.false(valu.startswith('0x'))

            nodes = await core.nodes('crypto:currency:transaction:hash')
            self.len(1, nodes)
            valu = nodes[0].get('hash')  # type: str
            self.false(valu.startswith('0x'))

            # storm migrations
            nodes = await core.nodes('geo:name')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'big hollywood sign')

            self.len(0, await core.nodes('crypto:currency:transaction:inputs'))
            self.len(0, await core.nodes('crypto:currency:transaction:outputs'))

            nodes = await core.nodes('crypto:payment:input=(i1,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes('crypto:payment:input=(i2,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:input=(i2,) -> crypto:currency:transaction +crypto:currency:transaction=(t2,)')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:input=(i2,) -> crypto:currency:transaction +crypto:currency:transaction=(t3,)')
            self.len(0, nodes)
            nodes = await core.nodes('crypto:payment:input=(i3,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes('crypto:payment:output=(o1,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes('crypto:payment:output=(o2,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:output=(o2,) -> crypto:currency:transaction +crypto:currency:transaction=(t2,)')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:output=(o2,) -> crypto:currency:transaction +crypto:currency:transaction=(t3,)')
            self.len(0, nodes)
            nodes = await core.nodes('crypto:payment:output=(o3,) -> crypto:currency:transaction')
            self.len(1, nodes)
            self.len(0, await core.nodes('crypto:payment:input=(i4,) -> crypto:currency:transaction'))
            self.len(0, await core.nodes('crypto:payment:output=(o4,) -> crypto:currency:transaction'))

    async def test_modelrev_0_2_9(self):

        async with self.getRegrCore('model-0.2.9') as core:

            # test ou:industry:name -> ou:industryname
            nodes = await core.nodes('ou:industry -> ou:industryname')
            self.len(1, nodes)
            self.eq('foo bar', nodes[0].ndef[1])
            self.len(1, await core.nodes('ou:industryname="foo bar" -> ou:industry'))

            # test the various it:prod:softname conversions
            nodes = await core.nodes('it:prod:soft -> it:prod:softname')
            self.len(3, nodes)
            self.eq(('foo bar', 'baz faz', 'hehe haha'), [n.ndef[1] for n in nodes])

            nodes = await core.nodes('it:prod:softver -> it:prod:softname')
            self.len(3, nodes)
            self.eq(('foo bar', 'baz faz', 'hehe haha'), [n.ndef[1] for n in nodes])

            nodes = await core.nodes('it:mitre:attack:software -> it:prod:softname')
            self.len(3, nodes)
            self.eq(('foo bar', 'baz faz', 'hehe haha'), [n.ndef[1] for n in nodes])

            # test :name pivots
            self.len(1, await core.nodes('it:prod:softname="foo bar" -> it:prod:soft'))
            self.len(1, await core.nodes('it:prod:softname="foo bar" -> it:prod:softver'))
            self.len(1, await core.nodes('it:prod:softname="foo bar" -> it:mitre:attack:software'))

            # test :names pivots
            self.len(1, await core.nodes('it:prod:softname="baz faz" -> it:prod:soft'))
            self.len(1, await core.nodes('it:prod:softname="baz faz" -> it:prod:softver'))
            self.len(1, await core.nodes('it:prod:softname="baz faz" -> it:mitre:attack:software'))

    async def test_modelrev_0_2_10(self):

        async with self.getRegrCore('model-0.2.10') as core:

            nodes = await core.nodes('it:av:filehit -> it:av:signame')
            self.len(1, nodes)
            self.eq('baz', nodes[0].ndef[1])

            self.len(1, await core.nodes('it:av:signame=foobar -> it:av:sig'))

            self.len(1, await core.nodes('it:av:signame=baz -> it:av:filehit'))

    async def test_modelrev_0_2_11(self):

        async with self.getRegrCore('model-0.2.11') as core:

            nodes = await core.nodes('crypto:x509:cert=30afb0317adcaf40dab85031b90e42ad')
            self.len(1, nodes)
            self.eq(nodes[0].get('serial'), '0000000000000000000000000000000000000001')

            nodes = await core.nodes('crypto:x509:cert=405b08fca9724ac1122f934e2e4edb3c')
            self.len(1, nodes)
            self.eq(nodes[0].get('serial'), '0000000000000000000000000000000000003039')

            nodes = await core.nodes('crypto:x509:cert=6bee0d34d52d60ca867409f2bf775dab')
            self.len(1, nodes)
            self.eq(nodes[0].get('serial'), 'ffffffffffffffffffffffffffffffffffffcfc7')

            nodes = await core.nodes('crypto:x509:cert=9ece91b7d5b8177488c1168f04ae0bc0')
            self.len(1, nodes)
            self.eq(nodes[0].get('serial'), '00000000000000000000000000000000000000ff')

            nodes = await core.nodes('crypto:x509:cert=8fc59ed63522b50bd31f2d138dd8c8ec $node.data.load(migration:0_2_10)')
            self.len(1, nodes)
            self.none(nodes[0].get('serial'))
            huge = '7307508186654514591018424163581415098279662714800'
            self.eq(nodes[0].nodedata['migration:0_2_10']['serial'], huge)

            nodes = await core.nodes('crypto:x509:cert=fb9545568c38002dcca1f66220c9ab7d $node.data.load(migration:0_2_10)')
            self.len(1, nodes)
            self.none(nodes[0].get('serial'))
            self.eq(nodes[0].nodedata['migration:0_2_10']['serial'], 'asdf')

            nodes = await core.nodes('ps:contact -> ou:jobtitle')
            self.len(2, nodes)
            self.eq(('cool guy', 'vice president'), [n.ndef[1] for n in nodes])

            self.len(1, await core.nodes('ou:jobtitle="vice president" -> ps:contact'))

    async def test_modelrev_0_2_12(self):
        async with self.getRegrCore('model-0.2.12') as core:
            self.len(1, await core.nodes('geo:name=woot'))
            self.len(1, await core.nodes('pol:country -> geo:name'))
            self.len(1, await core.nodes('risk:alert:taxonomy=hehe'))
            self.len(1, await core.nodes('risk:alert -> risk:alert:taxonomy'))

    async def test_modelrev_0_2_13(self):
        async with self.getRegrCore('model-0.2.13') as core:
            self.len(1, await core.nodes('risk:tool:software:taxonomy=testtype'))
            self.len(1, await core.nodes('risk:tool:software -> risk:tool:software:taxonomy'))

    async def test_modelrev_0_2_14(self):
        async with self.getRegrCore('model-0.2.14') as core:
            self.len(1, await core.nodes('inet:flow:dst:softnames*[=foo]'))
            self.len(1, await core.nodes('inet:flow:src:softnames*[=bar]'))
            self.len(1, await core.nodes('inet:flow:dst:softnames=(baz, foo)'))
            self.len(1, await core.nodes('inet:flow:src:softnames=(bar, baz)'))
            self.len(1, await core.nodes('it:prod:softname=foo -> inet:flow:dst:softnames'))
            self.len(1, await core.nodes('it:prod:softname=bar -> inet:flow:src:softnames'))

    async def test_modelrev_0_2_15(self):
        async with self.getRegrCore('model-0.2.15') as core:
            nodes = await core.nodes('ou:contract:award:price=1.230')
            self.len(1, nodes)
            self.eq('1.23', nodes[0].props.get('award:price'))

            nodes = await core.nodes('ou:contract:budget:price=4.560')
            self.len(1, nodes)
            self.eq('4.56', nodes[0].props.get('budget:price'))

            nodes = await core.nodes('ou:contract -:award:price -:budget:price $node.data.load(migration:0_2_15)')
            self.len(1, nodes)
            data = nodes[0].nodedata['migration:0_2_15']
            self.eq(data['award:price'], 'foo')
            self.eq(data['budget:price'], 'bar')

    async def test_modelrev_0_2_16(self):
        async with self.getRegrCore('model-0.2.16') as core:
            nodes = await core.nodes('risk:tool:software=bb1b3ecd5ff61b52ebad87e639e50276')
            self.len(1, nodes)
            self.len(2, nodes[0].get('soft:names'))
            self.len(2, nodes[0].get('techniques'))

    async def test_modelrev_0_2_17(self):
        async with self.getRegrCore('model-0.2.17') as core:

            self.len(1, await core.nodes('risk:vuln:cvss:av=P'))
            self.len(1, await core.nodes('risk:vuln:cvss:av=L'))
            self.len(1, await core.nodes('inet:http:cookie:name=gronk -:value'))
            self.len(1, await core.nodes('inet:http:cookie:name=foo +:value=bar'))
            self.len(1, await core.nodes('inet:http:cookie:name=zip +:value="zop=zap"'))

    async def test_modelrev_0_2_18(self):

        async with self.getRegrCore('model-0.2.18') as core:

            nodes = await core.nodes('ou:goal:name="woot woot"')
            self.len(1, nodes)
            self.eq('foo.bar.baz.', nodes[0].get('type'))
            self.len(1, await core.nodes('ou:goal:name="woot woot" -> ou:goalname'))
            self.len(1, await core.nodes('ou:goal:name="woot woot" -> ou:goal:type:taxonomy'))

            nodes = await core.nodes('file:bytes:mime:pe:imphash -> hash:md5')
            self.len(1, nodes)
            self.eq(('hash:md5', 'c734c107793b4222ee690fed85e2ad4d'), nodes[0].ndef)

    async def test_modelrev_0_2_19(self):

        async with self.getRegrCore('model-0.2.19') as core:
            self.len(1, await core.nodes('ou:campname="operation overlord"'))
            self.len(1, await core.nodes('ou:campname="operation overlord" -> ou:campaign'))
            self.len(1, await core.nodes('risk:vuln:type:taxonomy="cyber.int_overflow" -> risk:vuln'))

        with self.getAsyncLoggerStream('synapse.lib.modelrev',
                                       'error re-norming risk:vuln:type=foo.bar...newp') as stream:
            async with self.getRegrCore('model-0.2.19-bad-risk-types') as core:
                self.true(await stream.wait(timeout=6))
                self.len(5, await core.nodes('risk:vuln'))
                self.len(4, await core.nodes('risk:vuln:type'))
                nodes = await core.nodes('yield $lib.lift.byNodeData(_migrated:risk:vuln:type)')
                self.len(1, nodes)
                node = nodes[0]
                self.none(node.get('type'))
                self.eq(node.nodedata.get('_migrated:risk:vuln:type'), 'foo.bar...newp')

    async def test_modelrev_0_2_20(self):

        async with self.getRegrCore('model-0.2.20') as core:
            self.len(1, await core.nodes('inet:user="visi@vertex.link" -> inet:url'))
            self.len(1, await core.nodes('inet:passwd="secret@" -> inet:url'))

            md5 = 'e66a62b251fcfbbc930b074503d08542'
            nodes = await core.nodes(f'hash:md5={md5} -> file:bytes')
            self.len(1, nodes)
            self.eq(md5, nodes[0].props.get('mime:pe:imphash'))

    async def test_modelrev_0_2_21(self):

        cvssv2 = 'AV:L/AC:L/Au:M/C:P/I:C/A:N/E:ND/RL:TF/RC:ND/CDP:ND/TD:ND/CR:ND/IR:ND/AR:ND'
        cvssv3 = 'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/E:U/RL:O/RC:U/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X'

        async with self.getRegrCore('model-0.2.21') as core:
            nodes = await core.nodes('risk:vuln=(foo,)')
            self.len(1, nodes)

            self.eq(nodes[0].props.get('cvss:v2'), s_chop.cvss2_normalize(cvssv2))
            self.eq(nodes[0].props.get('cvss:v3'), s_chop.cvss3x_normalize(cvssv3))

            self.len(1, await core.nodes('risk:vulnname="woot woot"'))
            self.len(1, await core.nodes('risk:vuln:name="woot woot"'))

    async def test_modelrev_0_2_22(self):

        async with self.getRegrCore('model-0.2.22') as core:
            nodes = await core.nodes('inet:ipv4=100.64.0.0/10')
            self.len(257, nodes)

            for node in nodes:
                self.eq(node.props.get('type'), 'shared')

    async def test_modelrev_0_2_23(self):
        async with self.getRegrCore('model-0.2.23') as core:
            self.len(1, await core.nodes('inet:ipv6="ff01::1" +:type=multicast +:scope=interface-local'))

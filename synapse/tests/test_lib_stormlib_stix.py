import copy
import json

import synapse.exc as s_exc

import synapse.lib.stormlib.stix as s_stix

import synapse.tests.utils as s_test

# flake8: noqa: E501

class StormlibModelTest(s_test.SynTest):

    def bundeq(self, bund0, bund1):

        bund0 = copy.deepcopy(bund0)
        bund1 = copy.deepcopy(bund1)

        self._stripStixBundle(bund0)
        self._stripStixBundle(bund1)

        def fx(b):
            return b['id']

        objs0 = list(sorted(bund0['objects'], key=fx))
        objs1 = list(sorted(bund1['objects'], key=fx))

        for i in range(max(len(objs0), len(objs1))):
            self.eq(objs0[i], objs1[i])

    def _stripStixBundle(self, bund):
        bund.pop('id', None)
        for sobj in bund['objects']:
            sobj.pop('created', None)
            sobj.pop('modified', None)
            sobj.pop('valid_from', None)

    def getTestBundle(self, name):
        path = self.getTestFilePath('stix_export', name)
        with open(path, 'r') as fd:
            return json.load(fd)

    def setTestBundle(self, name, bund):
        path = self.getTestFilePath('stix_export', name)
        with open(path, 'w') as fd:
            json.dump(bund, fd, sort_keys=True, indent=2)

    def reqValidStix(self, item):
        resp = s_stix.validateStix(item)
        success = resp.get('ok')
        if not success:
            self.true(success)

    async def test_stormlib_libstix(self, conf=None):

        async with self.getTestCore(conf=conf) as core:
            opts = {'vars': {
                'ind': '6ba7d8500964902bf2e03126ed0f6cb1',
                'news': '840b9b003a765020705ea8d203a7659c',
                'goal': '940b9b003a765020705ea8d203a7659c',
                'place': 'c0254e1d0f9dedb0a03e2b95a55428eb',
                'attack': '6a07c4b0789fd9ea73e7bfe54fb3c724',
                'contact': 'a0861d3024462211ba5aaa47abaff458',
                'message': '41750ef970b825675004ff8012838d5e',
                'campaign': '21592cce6e1532dee5e348bfc4481e6b',
                'yararule': '2f200ad524a2e7e56830f9bab6220892',
                'snortrule': '73e8073e66b2833c12184094d3433ebb',
                'targetorg': 'c915178f2ddd08145ff48ccbaa551873',
                'attackorg': 'd820b6d58329662bc5cabec03ef72ffa',

                'softver': 'a920b6d58329662bc5cabec03ef72ffa',
                'prodsoft': 'a120b6d58329662bc5cabec03ef72ffa',

                'sha256': '00001c4644c1d607a6ff6fbf883873d88fe8770714893263e2dfb27f291a6c4e',
                'sha256': '00001c4644c1d607a6ff6fbf883873d88fe8770714893263e2dfb27f291a6c4e',
            }}

            self.len(22, await core.nodes('''[
                (inet:asn=30 :name=woot30)
                (inet:asn=40 :name=woot40)
                (inet:ipv4=1.2.3.4 :asn=30)
                (inet:ipv6="::ff" :asn=40)
                inet:email=visi@vertex.link
                (ps:contact=* :name="visi stark" :email=visi@vertex.link)
                (ou:org=$targetorg :name=target :industries+={[ou:industry=$ind :name=aerospace]})
                (ou:org=$attackorg :name=attacker :hq={[geo:place=$place :loc=ru :name=moscow :latlong=(55.7558, 37.6173)]})
                (ou:campaign=$campaign :name=woot :org={ou:org:name=attacker} :goal={[ou:goal=$goal :name=pwning]})
                (risk:attack=$attack :campaign={ou:campaign} :target:org={ou:org:name=target})
                (it:app:yara:rule=$yararule :name=yararulez :text="rule dummy { condition: false }")
                (it:app:snort:rule=$snortrule :name=snortrulez :text="alert tcp 1.2.3.4 any -> 5.6.7.8 22 (msg:woot)")
                (inet:email:message=$message :subject=freestuff :to=visi@vertex.link :from=scammer@scammer.org)
                (media:news=$news :title=report0 :published=20210328 +(refs)> { inet:fqdn=vertex.link })
                (file:bytes=$sha256 :size=333 :name=woot.json :mime=application/json +(refs)> { inet:fqdn=vertex.link } +#cno.mal.redtree)
                (inet:web:acct=(twitter.com, invisig0th) :realname="visi stark" .seen=(2010,2021) :signup=2010 :passwd=secret)
                (syn:tag=cno.mal.redtree :title="Redtree Malware" .seen=(2010, 2020))
                (it:prod:soft=$prodsoft :name=rar)
                (it:prod:softver=$softver :software=$prodsoft .seen=(1996, 2021) :vers=2.0.1)
                inet:dns:a=(vertex.link, 1.2.3.4)
                inet:dns:aaaa=(vertex.link, "::ff")
                inet:dns:cname=(vertex.link, vtx.lk)
            ]''', opts=opts))

            self.len(1, await core.nodes('media:news -(refs)> *'))

            bund = await core.callStorm('''
                init { $bundle = $lib.stix.export.bundle() }

                inet:asn
                inet:ipv4
                inet:ipv6
                inet:email
                inet:web:acct
                media:news
                ou:org:name=target
                ou:campaign

                inet:fqdn=vtx.lk
                inet:fqdn=vertex.link

                file:bytes
                inet:email:message
                it:prod:softver

                it:app:yara:rule
                it:app:snort:rule

                $bundle.add($node)

                | spin | syn:tag=cno.mal.redtree $bundle.add($node, stixtype=malware)

                fini { return($bundle) }
            ''')

            self.reqValidStix(bund)

            self.bundeq(self.getTestBundle('basic.json'), bund)

            opts = {'vars': {
                'file': 'guid:64610b9fdc23964d27f5d84f395a76df',
                'execurl': 'f248920f711cd2ea2c5bec139d82ce0b',
            }}

            bund = await core.callStorm('''
                init {
                    $config = $lib.stix.export.config()

                    $config.forms."syn:tag".stix.malware.rels.append(
                        (communicates-with, url, ${-> file:bytes -> it:exec:url:exe -> inet:url})
                    )

                    $config.forms."syn:tag".stix.malware.props.name = ${return(redtree)}
                    $bundle = $lib.stix.export.bundle(config=$config)
                }

                [ syn:tag=cno.mal.redtree ]

                {[( file:bytes=$file +#cno.mal.redtree )]}
                {[( it:exec:url=$execurl :exe=$file :url=http://vertex.link/ )]}

                $bundle.add($node, stixtype=malware)

                fini { return($bundle) }
            ''', opts=opts)

            self.reqValidStix(bund)

            self.bundeq(self.getTestBundle('custom0.json'), bund)

            resp = await core.callStorm('return($lib.stix.validate($bundle))', {'vars': {'bundle': bund}})
            self.true(resp.get('ok'))
            result = resp.get('result')
            self.eq(result, {'result': True})

            bad_bundle = copy.deepcopy(bund)
            objects = bad_bundle.get('objects')  # type: list
            extdef = objects[0]
            extdef.pop('type')
            resp = await core.callStorm('return($lib.stix.validate($bundle))', {'vars': {'bundle': bad_bundle}})
            self.false(resp.get('ok'))
            self.isin('Error validating bundle', resp.get('mesg'))

            nodes = await core.nodes('yield $lib.stix.lift($bundle)', {'vars': {'bundle': bund}})
            self.len(10, nodes)

            # test some sad paths...
            self.none(await core.callStorm('return($lib.stix.export.bundle().add($lib.true))'))
            self.none(await core.callStorm('[ ou:conference=* ] return($lib.stix.export.bundle().add($node))'))
            self.none(await core.callStorm('[ inet:fqdn=vertex.link ] return($lib.stix.export.bundle().add($node, stixtype=foobar))'))

            with self.raises(s_exc.BadConfValu):
                config = {'maxsize': 'woot'}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.BadConfValu):
                config = {'maxsize': 10000000}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.NoSuchForm):
                config = {'forms': {'hehe:haha': {}}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.NeedConfValu):
                config = {'forms': {'inet:fqdn': {}}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.BadConfValu):
                config = {'forms': {'inet:fqdn': {'default': 'newp'}}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.NeedConfValu):
                config = {'forms': {'inet:fqdn': {'default': 'domain-name'}}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.BadConfValu):
                config = {'forms': {'inet:fqdn': {'default': 'domain-name', 'stix': {}}}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.BadConfValu):
                config = {'forms': {'inet:fqdn': {
                                'default': 'domain-name',
                                'stix': {
                                    'domain-name': {},
                                    'newp': {},
                                },
                         }}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.BadConfValu):
                config = {'forms': {'inet:fqdn': {
                                'default': 'domain-name',
                                'stix': {
                                    'domain-name': {
                                        'props': {'foo': 10},
                                    },
                                },
                         }}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.BadConfValu):
                config = {'forms': {'inet:fqdn': {
                                'default': 'domain-name',
                                'stix': {
                                    'domain-name': {
                                        'rels': (
                                            (1, 2, 3, 4),
                                        ),
                                    },
                                },
                         }}}
                opts = {'vars': {'config': config}}
                await core.callStorm('$lib.stix.export.bundle(config=$config)', opts=opts)

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('''
                    init {
                        $config = $lib.stix.export.config()
                        $config.maxsize = (1)

                        $bundle = $lib.stix.export.bundle(config=$config)
                    }

                    inet:fqdn $bundle.add($node)
                ''')

    async def test_risk_vuln(self):
        async with self.getTestCore() as core:
            await core.nodes('''[(risk:vuln=(vuln1,) :name=vuln1 :desc="bad vuln" :cve="cve-2013-0000")]
            [(risk:vuln=(vuln3,) :name="bobs version of cve-2013-001" :cve="cve-2013-0001")]
            [(ou:org=(bob1,) :name="bobs whitehatz")]
            [(ou:campaign=(campaign1,) :name="bob hax" :org=(bob1,) )]
            [(risk:attack=(attk1,) :used:vuln=(vuln1,) :campaign=(campaign1,) )]
            [(risk:attack=(attk2,) :used:vuln=(vuln3,) :campaign=(campaign1,) )]
            ''')

            bund = await core.callStorm('''
            init { $bundle = $lib.stix.export.bundle() }
            ou:campaign
            $bundle.add($node)
            fini { return($bundle) }''')
            self.reqValidStix(bund)
            self.bundeq(self.getTestBundle('risk0.json'), bund)

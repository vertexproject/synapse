import copy
import json

import synapse.common as s_common
import synapse.tests.utils as s_test

import synapse.lib.stormlib.stix as s_stix

class StormlibModelTest(s_test.SynTest):

    async def test_stormlib_stix_uuid_covert(self):
        buid = b'\xa5\x5a' * 16
        uuid = s_stix._buid_to_uuid4(buid)
        self.len(36, uuid)
        buidpre = s_stix._uuid4_to_buidpre(uuid)
        self.true(buid.startswith(buidpre))

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

    def getTestBundle(self, name):
        path = self.getTestFilePath('stix_export', name)
        with open(path, 'r') as fd:
            return json.load(fd)

    def setTestBundle(self, name, bund):
        path = self.getTestFilePath('stix_export', name)
        with open(path, 'w') as fd:
            json.dump(bund, fd, sort_keys=True, indent=2)

    async def test_stormlib_libstix(self):

        async with self.getTestCore() as core:
            opts = {'vars': {
                'place': 'c0254e1d0f9dedb0a03e2b95a55428eb',
                'attack': '6a07c4b0789fd9ea73e7bfe54fb3c724',
                'contact': 'a0861d3024462211ba5aaa47abaff458',
                'message': '41750ef970b825675004ff8012838d5e',
                'campaign': '21592cce6e1532dee5e348bfc4481e6b',
                'yararule': '2f200ad524a2e7e56830f9bab6220892',
                'snortrule': '73e8073e66b2833c12184094d3433ebb',
                'targetorg': 'c915178f2ddd08145ff48ccbaa551873',
                'attackorg': 'd820b6d58329662bc5cabec03ef72ffa',
            }}

            self.len(16, await core.nodes('''[
                (inet:asn=30 :name=woot30)
                (inet:asn=40 :name=woot40)
                (inet:ipv4=1.2.3.4 :asn=30)
                (inet:ipv6="::ff" :asn=40)
                inet:email=visi@vertex.link
                (ps:contact=* :name="visi stark" :email=visi@vertex.link)
                (ou:org=$targetorg :name=target)
                (ou:org=$attackorg :name=attacker :hq={[geo:place=$place :loc=ru :name=moscow :latlong=(55.7558, 37.6173)]})
                (ou:campaign=$campaign :name=woot :org={ou:org:name=attacker})
                (risk:attack=$attack :campaign={ou:campaign} :target:org={ou:org:name=target})
                (it:app:yara:rule=$yararule :name=yararulez :text="rule dummy { condition: false }")
                (it:app:snort:rule=$snortrule :name=snortrulez :text="alert tcp 1.2.3.4 any -> 5.6.7.8 22 (msg:woot)")
                (inet:email:message=$message :subject=freestuff :to=visi@vertex.link :from=scammer@scammer.org)
                inet:dns:a=(vertex.link, 1.2.3.4)
                inet:dns:aaaa=(vertex.link, "::ff")
                inet:dns:cname=(vertex.link, vtx.lk)
            ]''', opts=opts))

            bund = await core.callStorm('''
                init { $bundle = $lib.stix.export.bundle() }

                inet:asn
                inet:ipv4
                inet:ipv6
                inet:fqdn
                inet:email
                ou:org:name=target
                ou:campaign

                it:app:yara:rule
                it:app:snort:rule

                $bundle.add($node)

                fini { return($bundle) }
            ''')
            #self.setTestBundle('basic.json', bund)
            self.bundeq(bund, self.getTestBundle('basic.json'))

            opts = {'vars': {
                'file': 'guid:64610b9fdc23964d27f5d84f395a76df',
                'execurl': 'f248920f711cd2ea2c5bec139d82ce0b',
            }}

            bund = await core.callStorm('''
                init {
                    $config = $lib.stix.export.config()

                    $config."file:bytes".stix.malware.rels.append(
                        (communicates-with, url, ${-> it:exec:url:exe -> inet:url}, $lib.dict()),
                    )

                    $config."file:bytes".stix.malware.props.name = (${return(redtree)}, $lib.dict())

                    $bundle = $lib.stix.export.bundle(config=$config)
                }

                [ file:bytes=$file +#cno.mal.redtree ]

                {[( it:exec:url=$execurl :exe=$file :url=http://vertex.link/ )]}

                $bundle.add($node, stixtype=malware)

                fini { return($bundle) }
            ''', opts=opts)

            #self.setTestBundle('custom0.json', bund)
            self.bundeq(bund, self.getTestBundle('custom0.json'))

            return

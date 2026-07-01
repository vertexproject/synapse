import synapse.common as s_common
import synapse.lib.time as s_time

import synapse.tests.utils as s_t_utils

class PsModelTest(s_t_utils.SynTest):
    async def test_ps_simple(self):

        person0 = s_common.guid()
        persona0 = s_common.guid()
        file0 = 'sha256:' + 64 * '0'
        org0 = s_common.guid()
        con0 = s_common.guid()
        place = s_common.guid()

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                ps:person=*
                    :photo={[ file:bytes=* ]}
                    :name='robert clown grey'
                    :names=('Billy Bob', 'Billy bob')
                    :lifespan=(1971, 20501217)
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('photo'))
            self.propeq(nodes[0], 'name', 'robert clown grey')
            self.propeq(nodes[0], 'names', ('Billy Bob', 'Billy bob'))
            self.propeq(nodes[0], 'lifespan', (31536000000000, 2554848000000000, 2523312000000000))

            # the names array preserves case so the two "Billy" casings are distinct
            # array elements that deconflict to a single entity:name node
            self.len(2, await core.nodes('ps:person -> entity:name | uniq'))
            self.len(1, await core.nodes('ps:person :photo -> file:bytes'))

            # ps:person implements the risk:targetable interface
            self.isin('risk:targetable', core.model.form('ps:person').ifaces)
            self.len(1, await core.nodes('ps:person { [ <(targeted)+ {[ entity:contact=({"name": "apt1"}) ]} ] }'))
            self.len(1, await core.nodes('ps:person <(targeted)- entity:contact'))

            nodes = await core.nodes('''
                [ meta:award=* :name="Bachelors of Science" :type=degree :issuer={[ ou:org=* ]} ]
            ''')
            self.nn(nodes[0].get('issuer'))
            self.propeq(nodes[0], 'name', 'Bachelors of Science')
            self.propeq(nodes[0], 'type', 'degree.')

            nodes = await core.nodes('''
                [
                    edu:class=*
                    :name="Chem 101 Spring 2026"
                    :desc="introductory chemistry"
                    :type=college.undergrad
                    :course=* as edu:course
                    :instructor={[ entity:contact=* ]}
                    :assistants={[ entity:contact=* ]}
                    :period=(20200202, 20210202)
                    :remote=50
                    :remote:url=https://vertex.edu/chem101
                    :remote:provider={[ entity:contact=* ]}
                    :remote:provider:name="vertex remote"
                    :place={[ geo:place=* :name="vertex hall" ]}
                    :place:loc=us.va.reston
                    :place:country:code=us
                ]
            ''')
            self.len(1, nodes)
            self.true(core.model.form('edu:class').implements('entity:attendable'))
            self.propeq(nodes[0], 'name', 'Chem 101 Spring 2026')
            self.propeq(nodes[0], 'desc', 'introductory chemistry')
            self.propeq(nodes[0], 'type', 'college.undergrad.')
            self.propeq(nodes[0], 'remote', '50')
            self.propeq(nodes[0], 'remote:provider:name', 'vertex remote')
            self.propeq(nodes[0], 'place:loc', 'us.va.reston')
            self.propeq(nodes[0], 'place:country:code', 'us')
            self.nn(nodes[0].get('remote:provider'))
            self.nn(nodes[0].get('place'))
            self.eq(nodes[0].getProps(virts=True)['period.precision'], s_time.PREC_DAY)
            self.eq(nodes[0].pack(virts=True)[1]['props']['period.precision'], s_time.PREC_DAY)
            self.len(1, await core.nodes('edu:class -> geo:place +:name="vertex hall"'))
            self.len(1, await core.nodes('edu:class:remote:url=https://vertex.edu/chem101'))

            self.len(1, await core.nodes('edu:class -> edu:class:type:taxonomy'))
            self.len(1, await core.nodes('edu:class:type:taxonomy=college.undergrad'))

            nodes = await core.nodes('''
                [
                    edu:class=*
                    :name="Chem 101 Lab"
                    :activity={ edu:class:name="chem 101 spring 2026" }
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('activity'))
            self.len(1, await core.nodes('edu:class:name="chem 101 lab" +:activity'))
            self.len(1, await core.nodes('edu:class:name="chem 101 lab" :activity -> edu:class +:name="chem 101 spring 2026"'))

            course = (await core.nodes('edu:class:name="chem 101 spring 2026"'))[0].get('course')[1]
            opts = {'vars': {'course': course}}

            nodes = await core.nodes('''
                edu:course=$course
                [
                    :id=chem101
                    :name="Data Structure Analysis"
                    :desc="A brief description here"
                    :institution={[ ou:org=* ]}
                    :prereqs = ({[ edu:course=* ]},)
                ]
            ''', opts=opts)
            self.len(1, nodes)

            self.len(1, await core.nodes('edu:course=$course :prereqs -> edu:course', opts=opts))

            nodes = await core.nodes('''[
                ps:workhist = *
                    :org = * as ou:org
                    :org:name = WootCorp
                    :org:fqdn = wootwoot.com
                    :desc = "Wooting."
                    :contact = {[ entity:contact=* ]}
                    :job:type = it.dev
                    :employment:type = fulltime.salary
                    :title = "Python Developer"
                    :period=(20210731, 20220731)
                    :pay = 200000
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'org:name', 'WootCorp')
            self.propeq(nodes[0], 'org:fqdn', 'wootwoot.com')
            self.propeq(nodes[0], 'desc', 'Wooting.')
            self.propeq(nodes[0], 'job:type', 'it.dev.')
            self.propeq(nodes[0], 'employment:type', 'fulltime.salary.')
            self.propeq(nodes[0], 'title', 'Python Developer')
            self.propeq(nodes[0], 'period', (1627689600000000, 1659225600000000, 31536000000000))
            self.propeq(nodes[0], 'pay', '200000')

            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('contact'))

            self.len(1, await core.nodes('ps:workhist -> ou:org'))
            self.len(1, await core.nodes('ps:workhist -> entity:title'))
            self.len(1, await core.nodes('ps:workhist -> entity:contact'))
            self.len(1, await core.nodes('ps:workhist -> ou:employment:type:taxonomy'))
            nodes = await core.nodes('''
                ou:employment:type:taxonomy=fulltime.salary
                [ :name=FullTime :sort=9 ]
                +:base=salary +:parent=fulltime +:depth=1
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'FullTime')
            self.propeq(nodes[0], 'sort', 9)

            self.len(2, await core.nodes('ou:employment:type:taxonomy^=fulltime'))
            self.len(1, await core.nodes('ou:employment:type:taxonomy:base^=salary'))

    async def test_ps_vitals(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ps:vitals=*
                    :time=20220815
                    :individual={[ ps:person=* ]}
                    :econ:net:worth=100
                    :econ:annual:income=1000
                    :phys:mass=100lbs
                    :phys:height=6feet
                ]
                { -> ps:person [ :vitals={ps:vitals} ] }
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'time', 1660521600000000)

            self.propeq(nodes[0], 'phys:height', 1828)
            self.propeq(nodes[0], 'phys:mass', '45359.2')

            self.propeq(nodes[0], 'econ:net:worth', '100')
            self.propeq(nodes[0], 'econ:annual:income', '1000')

            self.nn(nodes[0].get('individual'))

            self.len(1, await core.nodes('ps:person :vitals -> ps:vitals'))

    async def test_ps_skillz(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ entity:proficiency=*
                    :actor = {[ entity:contact=* :name=visi ]}
                    :skill = {[ ps:skill=* :type=hungry :name="Wanting Pizza" ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('skill'))
            self.nn(nodes[0].get('actor'))
            self.len(1, await core.nodes('entity:proficiency -> entity:contact +:name=visi'))
            self.len(1, await core.nodes('entity:proficiency -> ps:skill +:name="wanting pizza"'))
            self.len(1, await core.nodes('entity:proficiency -> ps:skill -> ps:skill:type:taxonomy'))

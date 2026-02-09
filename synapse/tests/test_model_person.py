import synapse.common as s_common

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
            self.propeq(nodes[0], 'names', ('billy bob',))
            self.propeq(nodes[0], 'lifespan', (31536000000000, 2554848000000000, 2523312000000000))

            self.len(2, await core.nodes('ps:person -> entity:name'))
            self.len(1, await core.nodes('ps:person :photo -> file:bytes'))

            nodes = await core.nodes('''[
                ps:achievement=*
                    :award=*
                    :awardee={[ entity:contact=* ]}
                    :awarded=20200202
                    :expires=20210202
                    :revoked=20201130
            ]''')
            self.len(1, nodes)
            achv = nodes[0].ndef[1]

            nodes = await core.nodes('''
                ou:award [ :name="Bachelors of Science" :type=degree :org=* ]
            ''')
            self.nn(nodes[0].get('org'))
            self.propeq(nodes[0], 'name', 'bachelors of science')
            self.propeq(nodes[0], 'type', 'degree.')

            opts = {'vars': {'achv': achv}}
            nodes = await core.nodes('''[
                ps:education=*
                    :student={[ entity:contact=* ]}
                    :institution={[ entity:contact=* ]}
                    :period=(20200202, 20210202)
                    :achievement = $achv

                    +(included)> {[ edu:class=* ]}
            ]''', opts=opts)

            nodes = await core.nodes('''
                edu:class
                [
                    :course=*
                    :instructor={[ entity:contact=* ]}
                    :assistants={[ entity:contact=* ]}
                    :period=(20200202, 20210202)
                    :isvirtual=1
                    :virtual:url=https://vertex.edu/chem101
                    :virtual:provider={[ entity:contact=* ]}
                    :place=*
                ]
            ''')
            self.len(1, nodes)

            course = nodes[0].get('course')
            opts = {'vars': {'course': course}}

            nodes = await core.nodes('''
                edu:course=$course
                [
                    :id=chem101
                    :name="Data Structure Analysis"
                    :desc="A brief description here"
                    :institution={[ entity:contact=* ]}
                    :prereqs = (*,)
                ]
            ''', opts=opts)
            self.len(1, nodes)

            self.len(1, await core.nodes('edu:course=$course :prereqs -> edu:course', opts=opts))

            nodes = await core.nodes('''[
                ps:workhist = *
                    :org = *
                    :org:name = WootCorp
                    :org:fqdn = wootwoot.com
                    :desc = "Wooting."
                    :contact = {[ entity:contact=* ]}
                    :job:type = it.dev
                    :employment:type = fulltime.salary
                    :title = "Python Developer"
                    :period=(20210731, 20220731)
                    :pay = 200000
                    :pay:currency = usd
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'org:name', 'wootcorp')
            self.propeq(nodes[0], 'org:fqdn', 'wootwoot.com')
            self.propeq(nodes[0], 'desc', 'Wooting.')
            self.propeq(nodes[0], 'job:type', 'it.dev.')
            self.propeq(nodes[0], 'employment:type', 'fulltime.salary.')
            self.propeq(nodes[0], 'title', 'python developer')
            self.propeq(nodes[0], 'period', (1627689600000000, 1659225600000000, 31536000000000))
            self.propeq(nodes[0], 'pay', '200000')
            self.propeq(nodes[0], 'pay:currency', 'usd')

            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('contact'))

            self.len(1, await core.nodes('ps:workhist -> ou:org'))
            self.len(1, await core.nodes('ps:workhist -> entity:title'))
            self.len(1, await core.nodes('ps:workhist -> entity:contact'))
            self.len(1, await core.nodes('ps:workhist -> ou:employment:type:taxonomy'))
            nodes = await core.nodes('''
                ou:employment:type:taxonomy=fulltime.salary
                [ :title=FullTime :sort=9 ]
                +:base=salary +:parent=fulltime +:depth=1
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'title', 'FullTime')
            self.propeq(nodes[0], 'sort', 9)

            self.len(2, await core.nodes('ou:employment:type:taxonomy^=fulltime'))
            self.len(1, await core.nodes('ou:employment:type:taxonomy:base^=salary'))

    async def test_ps_vitals(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ps:vitals=*
                    :time=20220815
                    :individual={[ ps:person=* ]}
                    :econ:currency=usd
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

            self.propeq(nodes[0], 'econ:currency', 'usd')
            self.propeq(nodes[0], 'econ:net:worth', '100')
            self.propeq(nodes[0], 'econ:annual:income', '1000')

            self.nn(nodes[0].get('individual'))

            self.len(1, await core.nodes('ps:person :vitals -> ps:vitals'))

    async def test_ps_skillz(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ps:proficiency=*
                    :contact = {[ entity:contact=* :name=visi ]}
                    :skill = {[ ps:skill=* :type=hungry :name="Wanting Pizza" ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('skill'))
            self.nn(nodes[0].get('contact'))
            self.len(1, await core.nodes('ps:proficiency -> entity:contact +:name=visi'))
            self.len(1, await core.nodes('ps:proficiency -> ps:skill +:name="wanting pizza"'))
            self.len(1, await core.nodes('ps:proficiency -> ps:skill -> ps:skill:type:taxonomy'))

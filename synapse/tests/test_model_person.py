import synapse.common as s_common

import synapse.tests.utils as s_t_utils

class PsModelTest(s_t_utils.SynTest):
    async def test_ps_simple(self):

        person0 = s_common.guid()
        persona0 = s_common.guid()

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('ps:tokn', ' BOB ')
                self.eq(node.ndef[1], 'bob')

                node = await snap.addNode('ps:name', ' robert GREY  the\t3rd  ')
                self.eq(node.ndef[1], 'robert grey the 3rd')
                file0 = 'sha256:' + 64 * '0'
                person_props = {
                    'dob': '1971',
                    'dod': '20501217',
                    'img': file0,
                    'photo': file0,
                    'nick': 'pennywise',
                    'name': 'robert clown grey',
                    'name:sur': 'grey',
                    'name:middle': 'clown',
                    'name:given': 'robert',
                    'nicks': ['pwise71', 'SoulchilD'],
                    'names': ['Billy Bob', 'Billy bob']
                }
                node = await snap.addNode('ps:person', person0, person_props)
                self.eq(node.ndef[1], person0)
                self.eq(node.get('img'), file0)
                self.eq(node.get('dob'), 31536000000)
                self.eq(node.get('dod'), 2554848000000)
                self.eq(node.get('nick'), 'pennywise')
                self.eq(node.get('name'), 'robert clown grey')
                self.eq(node.get('name:sur'), 'grey')
                self.eq(node.get('name:middle'), 'clown')
                self.eq(node.get('name:given'), 'robert')
                self.eq(node.get('nicks'), ['pwise71', 'soulchild'])
                self.eq(node.get('names'), ['billy bob'])
                self.eq(node.get('photo'), file0)

                persona_props = {
                    'dob': '2000',
                    'img': file0,
                    'nick': 'acid burn',
                    'person': person0,
                    'name': 'Эммануэль брат Гольдштейн',
                    'name:sur': 'Гольдштейн',
                    'name:middle': 'брат',
                    'name:given': 'эммануэль',
                    'nicks': ['beeper88', 'W1ntermut3'],
                    'names': ['Bob Ross']
                }
                node = await snap.addNode('ps:persona', persona0, persona_props)
                self.eq(node.ndef[1], persona0)
                self.eq(node.get('img'), file0)
                self.eq(node.get('dob'), 946684800000)
                self.eq(node.get('nick'), 'acid burn')
                self.eq(node.get('person'), person0)
                self.eq(node.get('name'), 'эммануэль брат гольдштейн')
                self.eq(node.get('name:sur'), 'гольдштейн')
                self.eq(node.get('name:middle'), 'брат')
                self.eq(node.get('name:given'), 'эммануэль')
                self.eq(node.get('nicks'), ['beeper88', 'w1ntermut3'])
                self.eq(node.get('names'), ['bob ross'])
                # self.eq(node.get('img'), '')  # fixme file:bytes
                # self.eq(node.get('guidname'), '')  # fixme guid aliases

                node = await snap.addNode('ps:person:has', (person0, ('test:str', 'sewer map')))
                self.eq(node.ndef[1], (person0, ('test:str', 'sewer map')))
                self.eq(node.get('person'), person0)
                self.eq(node.get('node'), ('test:str', 'sewer map'))
                self.eq(node.get('node:form'), 'test:str')

                node = await snap.addNode('ps:persona:has', (persona0, ('test:str', 'the gibson')))
                self.eq(node.ndef[1], (persona0, ('test:str', 'the gibson')))
                self.eq(node.get('persona'), persona0)
                self.eq(node.get('node'), ('test:str', 'the gibson'))
                self.eq(node.get('node:form'), 'test:str')

                org0 = s_common.guid()
                con0 = s_common.guid()
                place = s_common.guid()
                cprops = {
                    'org': org0,
                    'asof': '20080414',
                    'person': person0,
                    'name': 'Tony  Stark',
                    'title': 'CEO',
                    'place': place,
                    'orgname': 'Stark Industries, INC',
                    # 'img': '',  # fixme file:bytes
                    'user': 'ironman',
                    'web:acct': ('twitter.com', 'ironman'),
                    'web:group': ('twitter.com', 'avengers'),
                    'dob': '1976-12-17',
                    'dod': '20501217',
                    'birth:place': '*',
                    'birth:place:loc': 'us.va.reston',
                    'birth:place:name': 'Reston, VA, USA, Earth, Sol, Milkyway',
                    'death:place': '*',
                    'death:place:loc': 'us.va.reston',
                    'death:place:name': 'Reston, VA, USA, Earth, Sol, Milkyway',
                    'url': 'https://starkindustries.com/',
                    'email': 'tony.stark@gmail.com',
                    'email:work': 'tstark@starkindustries.com',
                    'phone': '12345678910',
                    'phone:fax': '12345678910',
                    'phone:work': '12345678910',
                    'address': '1 Iron Suit Drive, San Francisco, CA, 22222, USA',
                    'imid': (490154203237518, 310150123456789),
                    'names': ('vi', 'si'),
                    'emails': ('visi@vertex.link', 'v@vtx.lk'),
                    'web:accts': (('twitter.com', 'invisig0th'), ('twitter.com', 'vtxproject')),
                    'id:numbers': (('*', 'asdf'), ('*', 'qwer')),
                    'users': ('visi', 'invisigoth'),
                    'crypto:address': 'btc/1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
                }

                node = await snap.addNode('ps:contact', con0, cprops)
                self.eq(node.ndef[1], con0)
                self.eq(node.get('org'), org0)
                self.eq(node.get('asof'), 1208131200000)
                self.eq(node.get('person'), person0)
                self.eq(node.get('place'), place)
                self.eq(node.get('name'), 'tony stark')
                self.eq(node.get('title'), 'ceo')
                self.eq(node.get('orgname'), 'stark industries, inc')
                self.eq(node.get('user'), 'ironman')
                self.eq(node.get('web:acct'), ('twitter.com', 'ironman'))
                self.eq(node.get('web:group'), ('twitter.com', 'avengers'))
                self.eq(node.get('dob'), 219628800000)
                self.eq(node.get('dod'), 2554848000000)
                self.eq(node.get('url'), 'https://starkindustries.com/')
                self.eq(node.get('email'), 'tony.stark@gmail.com')
                self.eq(node.get('email:work'), 'tstark@starkindustries.com')
                self.eq(node.get('phone'), '12345678910')
                self.eq(node.get('phone:fax'), '12345678910')
                self.eq(node.get('phone:work'), '12345678910')
                self.eq(node.get('address'), '1 iron suit drive, san francisco, ca, 22222, usa')
                self.eq(node.get('imid'), (490154203237518, 310150123456789))
                self.eq(node.get('imid:imei'), 490154203237518)
                self.eq(node.get('imid:imsi'), 310150123456789)
                self.eq(node.get('names'), ('si', 'vi'))
                self.eq(node.get('emails'), ('v@vtx.lk', 'visi@vertex.link'))
                self.eq(node.get('web:accts'), (('twitter.com', 'invisig0th'), ('twitter.com', 'vtxproject')))
                self.eq(node.get('users'), ('invisigoth', 'visi'))
                self.eq(node.get('crypto:address'), ('btc', '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2'))
                self.len(2, node.get('id:numbers'))

                self.eq(node.get('birth:place:loc'), 'us.va.reston')
                self.eq(node.get('death:place:loc'), 'us.va.reston')
                self.eq(node.get('birth:place:name'), 'reston, va, usa, earth, sol, milkyway')
                self.eq(node.get('death:place:name'), 'reston, va, usa, earth, sol, milkyway')
                self.len(1, await core.nodes('ps:contact :birth:place -> geo:place'))
                self.len(1, await core.nodes('ps:contact :death:place -> geo:place'))

                nodes = await core.nodes('''[
                    ps:achievement=*
                        :award=*
                        :awardee=*
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
                self.eq('bachelors of science', nodes[0].get('name'))
                self.eq('degree', nodes[0].get('type'))

                opts = {'vars': {'achv': achv}}
                nodes = await core.nodes('''[
                    ps:education=*
                        :student = *
                        :institution = *
                        :attended:first = 20200202
                        :attended:last = 20210202
                        :classes = (*,)
                        :achievement = $achv
                ]''', opts=opts)

                nodes = await core.nodes('''
                    edu:class
                    [
                        :course=*
                        :instructor=*
                        :assistants=(*,)
                        :date:first = 20200202
                        :date:last = 20210202
                        :isvirtual = 1
                        :virtual:url = https://vertex.edu/chem101
                        :virtual:provider = *
                        :place = *
                    ]
                ''')
                self.len(1, nodes)
                course = nodes[0].get('course')

                nodes = await core.nodes(f'''
                    edu:course={course}
                    [
                        :name="Data Structure Analysis"
                        :desc="A brief description here"
                        :institution=*
                        :prereqs = (*,)
                        :code=chem101
                    ]
                ''')
                self.len(1, nodes)

                course = nodes[0].ndef[1]
                self.len(1, await core.nodes(f'edu:course={course} :prereqs -> edu:course'))

                nodes = await core.nodes(f'''[
                    ps:contactlist=*
                        :contacts=(*,*)
                        :source:host=*
                        :source:file=*
                        :source:acct=(twitter.com, invisig0th)
                ]''')
                self.len(1, nodes)
                self.len(1, await core.nodes('ps:contactlist -> it:host'))
                self.len(1, await core.nodes('ps:contactlist -> file:bytes'))
                self.len(2, await core.nodes('ps:contactlist -> ps:contact'))
                self.len(1, await core.nodes('ps:contactlist -> inet:web:acct'))

                nodes = await core.nodes('''[
                    ps:workhist = *
                        :org = *
                        :orgname = WootCorp
                        :orgfqdn = wootwoot.com
                        :contact = *
                        :jobtype = it.dev
                        :employment = fulltime.salary
                        :jobtitle = "Python Developer"
                        :started = 20210731
                        :ended = 20220731
                        :duration = (9999)
                        :pay = 200000
                        :currency = usd
                ]''')
                self.len(1, nodes)
                self.eq(nodes[0].get('orgname'), 'wootcorp')
                self.eq(nodes[0].get('orgfqdn'), 'wootwoot.com')
                self.eq(nodes[0].get('jobtype'), 'it.dev.')
                self.eq(nodes[0].get('employment'), 'fulltime.salary.')
                self.eq(nodes[0].get('jobtitle'), 'python developer')
                self.eq(nodes[0].get('started'), 1627689600000)
                self.eq(nodes[0].get('ended'), 1659225600000)
                self.eq(nodes[0].get('duration'), 9999)
                self.eq(nodes[0].get('pay'), '200000')
                self.eq(nodes[0].get('currency'), 'usd')

                self.nn(nodes[0].get('org'))
                self.nn(nodes[0].get('contact'))

                self.len(1, await core.nodes('ps:workhist -> ou:org'))
                self.len(1, await core.nodes('ps:workhist -> ps:contact'))
                self.len(1, await core.nodes('ps:workhist -> ou:jobtitle'))
                self.len(1, await core.nodes('ps:workhist -> ou:employment'))
                nodes = await core.nodes('''
                    ou:employment=fulltime.salary
                    [ :title=FullTime :summary=HeHe :sort=9 ]
                    +:base=salary +:parent=fulltime +:depth=1
                ''')
                self.len(1, nodes)
                self.eq(nodes[0].get('title'), 'FullTime')
                self.eq(nodes[0].get('summary'), 'HeHe')
                self.eq(nodes[0].get('sort'), 9)

                self.len(2, await core.nodes('ou:employment^=fulltime'))
                self.len(1, await core.nodes('ou:employment:base^=salary'))

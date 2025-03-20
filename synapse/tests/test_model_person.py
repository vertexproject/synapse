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

            nodes = await core.nodes('[ps:tokn=" BOB "]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ps:tokn', 'bob'))

            nodes = await core.nodes('[ps:name=" robert GREY  the\t3rd   "]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ps:name', 'robert grey the 3rd'))

            props = {
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
            opts = {'vars': {'valu': person0, 'p': props}}
            q = '''[(ps:person=$valu
            :img=$p.img :dob=$p.dob :dod=$p.dod :photo=$p.photo
            :nick=$p.nick :name=$p.name :name:sur=$p."name:sur"
            :name:middle=$p."name:middle" :name:given=$p."name:given"
            :nicks=$p.nicks :names=$p.names
            )]'''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ps:person', person0))
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

            self.len(1, nodes := await core.nodes('[ ps:person=({"name": "billy bob"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            props = {
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
            opts = {'vars': {'valu': persona0, 'p': props}}
            q = '''[(ps:persona=$valu
                    :img=$p.img :dob=$p.dob :person=$p.person
                    :nick=$p.nick :name=$p.name :name:sur=$p."name:sur"
                    :name:middle=$p."name:middle" :name:given=$p."name:given"
                    :nicks=$p.nicks :names=$p.names
                    )]'''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ps:persona', persona0))
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

            nodes = await core.nodes('[ps:person:has=($person, ("test:str", "sewer map"))]',
                                     opts={'vars': {'person': person0}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ps:person:has', (person0, ('test:str', 'sewer map'))))
            self.eq(node.get('person'), person0)
            self.eq(node.get('node'), ('test:str', 'sewer map'))
            self.eq(node.get('node:form'), 'test:str')

            nodes = await core.nodes('[ps:persona:has=($persona, ("test:str", "the gibson"))]',
                                     opts={'vars': {'persona': persona0}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('ps:persona:has', (persona0, ('test:str', 'the gibson'))))
            self.eq(node.get('persona'), persona0)
            self.eq(node.get('node'), ('test:str', 'the gibson'))
            self.eq(node.get('node:form'), 'test:str')

            props = {
                'org': org0,
                'asof': '20080414',
                'person': person0,
                'name': 'Tony  Stark',
                'title': 'CEO',
                'place': place,
                'place:name': 'The Shire',
                'orgname': 'Stark Industries, INC',
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
                'orgnames': ('vertex', 'project'),
                'emails': ('visi@vertex.link', 'v@vtx.lk'),
                'web:accts': (('twitter.com', 'invisig0th'), ('twitter.com', 'vtxproject')),
                'id:numbers': (('*', 'asdf'), ('*', 'qwer')),
                'users': ('visi', 'invisigoth'),
                'crypto:address': 'btc/1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
                'langs': (lang00 := s_common.guid(),),
            }
            opts = {'vars': {'valu': con0, 'p': props}}
            q = '''[(ps:contact=$valu
                    :id=" 9999Aa"
                    :bio="I am ironman."
                    :org=$p.org :asof=$p.asof :person=$p.person
                    :place=$p.place :place:name=$p."place:name" :name=$p.name
                    :title=$p.title :orgname=$p.orgname :user=$p.user
                    :titles=('hehe', 'hehe', 'haha')
                    :web:acct=$p."web:acct" :web:group=$p."web:group"
                    :dob=$p.dob :dod=$p.dod :url=$p.url
                    :email=$p.email :email:work=$p."email:work"
                    :phone=$p.phone :phone:fax=$p."phone:fax" :phone:work=$p."phone:work"
                    :address=$p.address :imid=$p.imid :names=$p.names :orgnames=$p.orgnames
                    :emails=$p.emails :web:accts=$p."web:accts" :users=$p.users
                    :crypto:address=$p."crypto:address" :id:numbers=$p."id:numbers"
                    :birth:place=$p."birth:place" :birth:place:loc=$p."birth:place:loc"
                    :birth:place:name=$p."birth:place:name"
                    :death:place=$p."death:place" :death:place:loc=$p."death:place:loc"
                    :death:place:name=$p."death:place:name"
                    :service:accounts=(*, *) :langs=$p.langs
                        )]'''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.ndef[1], con0)
            self.eq(node.get('org'), org0)
            self.eq(node.get('asof'), 1208131200000)
            self.eq(node.get('person'), person0)
            self.eq(node.get('place'), place)
            self.eq(node.get('place:name'), 'the shire')
            self.eq(node.get('name'), 'tony stark')
            self.eq(node.get('id'), '9999Aa')
            self.eq(node.get('bio'), 'I am ironman.')
            self.eq(node.get('title'), 'ceo')
            self.eq(node.get('titles'), ('haha', 'hehe'))
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
            self.eq(node.get('orgnames'), ('project', 'vertex'))
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
            self.len(2, await core.nodes('ps:contact :service:accounts -> inet:service:account'))

            opts = {
                'vars': {
                    'ctor': {
                        'email': 'v@vtx.lk',
                        'id:number': node.get('id:numbers')[0],
                        'lang': lang00,
                        'name': 'vi',
                        'orgname': 'vertex',
                        'title': 'haha',
                        'user': 'invisigoth',
                    },
                },
            }
            self.len(1, nodes := await core.nodes('[ ps:contact=$ctor ]', opts=opts))
            self.eq(node.ndef, nodes[0].ndef)

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
                    :source:account=(twitter.com, invisig0th)
            ]''')
            self.len(1, nodes)
            self.len(1, await core.nodes('ps:contactlist -> it:host'))
            self.len(1, await core.nodes('ps:contactlist -> file:bytes'))
            self.len(2, await core.nodes('ps:contactlist -> ps:contact'))
            self.len(1, await core.nodes('ps:contactlist -> inet:web:acct'))
            self.len(1, await core.nodes('ps:contactlist -> inet:service:account'))

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

    async def test_ps_vitals(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ps:vitals=*
                    :asof=20220815
                    :contact=*
                    :person=*
                    :height=6feet
                    :weight=200lbs
                    :econ:currency=usd
                    :econ:net:worth=100
                    :econ:annual:income=1000
                    :phys:mass=100lbs
                ]
                { -> ps:person [ :vitals={ps:vitals} ] }
                { -> ps:contact [ :vitals={ps:vitals} ] }
            ''')
            self.len(1, nodes)
            self.eq(1660521600000, nodes[0].get('asof'))
            self.eq(1828, nodes[0].get('height'))
            self.eq('90718.4', nodes[0].get('weight'))

            self.eq('45359.2', nodes[0].get('phys:mass'))

            self.eq('usd', nodes[0].get('econ:currency'))
            self.eq('100', nodes[0].get('econ:net:worth'))
            self.eq('1000', nodes[0].get('econ:annual:income'))

            self.nn(nodes[0].get('person'))
            self.nn(nodes[0].get('contact'))

            self.len(1, await core.nodes('ps:person :vitals -> ps:vitals'))
            self.len(1, await core.nodes('ps:contact :vitals -> ps:vitals'))

    async def test_ps_skillz(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ ps:proficiency=*
                    :contact = {[ ps:contact=* :name=visi ]}
                    :skill = {[ ps:skill=* :type=hungry :name="Wanting Pizza" ]}
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('skill'))
            self.nn(nodes[0].get('contact'))
            self.len(1, await core.nodes('ps:proficiency -> ps:contact +:name=visi'))
            self.len(1, await core.nodes('ps:proficiency -> ps:skill +:name="wanting pizza"'))
            self.len(1, await core.nodes('ps:proficiency -> ps:skill -> ps:skill:type:taxonomy'))

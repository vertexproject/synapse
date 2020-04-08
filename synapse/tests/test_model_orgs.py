import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class OuModelTest(s_t_utils.SynTest):

    async def test_ou_simple(self):

        async with self.getTestCore() as core:

            goal = s_common.guid()
            org0 = s_common.guid()
            camp = s_common.guid()

            async with await core.snap() as snap:

                props = {
                    'name': 'MyGoal',
                    'type': 'MyType',
                    'desc': 'MyDesc',
                    'prev': goal,
                }
                node = await snap.addNode('ou:goal', goal, props=props)
                self.eq(node.get('name'), 'MyGoal')
                self.eq(node.get('type'), 'MyType')
                self.eq(node.get('desc'), 'MyDesc')
                self.eq(node.get('prev'), goal)

                props = {
                    'stated': True,
                    'window': '2019,2020',
                }
                node = await snap.addNode('ou:hasgoal', (org0, goal), props=props)
                self.eq(node.get('org'), org0)
                self.eq(node.get('goal'), goal)
                self.eq(node.get('stated'), True)
                self.eq(node.get('window'), (1546300800000, 1577836800000))

                props = {
                    'org': org0,
                    'goal': goal,
                    'goals': (goal,),
                    'name': 'MyName',
                    'type': 'MyType',
                    'desc': 'MyDesc',
                }
                node = await snap.addNode('ou:campaign', camp, props=props)
                self.eq(node.get('org'), org0)
                self.eq(node.get('goal'), goal)
                self.eq(node.get('goals'), (goal,))
                self.eq(node.get('name'), 'MyName')
                self.eq(node.get('type'), 'MyType')
                self.eq(node.get('desc'), 'MyDesc')

            # type norming first
            # ou:name
            t = core.model.type('ou:name')
            norm, subs = t.norm('Acme Corp ')
            self.eq(norm, 'acme corp')

            # ou:naics
            t = core.model.type('ou:naics')
            norm, subs = t.norm(541715)
            self.eq(norm, '541715')
            self.raises(s_exc.BadTypeValu, t.norm, 'newp')
            self.raises(s_exc.BadTypeValu, t.norm, 1000000)
            self.raises(s_exc.BadTypeValu, t.norm, 1000)

            # ou:sic
            t = core.model.type('ou:sic')
            norm, subs = t.norm('7999')
            self.eq(norm, '7999')
            norm, subs = t.norm(9999)
            self.eq(norm, '9999')
            norm, subs = t.norm('0111')
            self.eq(norm, '0111')

            self.raises(s_exc.BadTypeValu, t.norm, -1)
            self.raises(s_exc.BadTypeValu, t.norm, 0)
            self.raises(s_exc.BadTypeValu, t.norm, 111)
            self.raises(s_exc.BadTypeValu, t.norm, 10000)

            # ou:alias
            t = core.model.type('ou:alias')
            self.raises(s_exc.BadTypeValu, t.norm, 'asdf.asdf.asfd')
            self.eq(t.norm('HAHA1')[0], 'haha1')
            self.eq(t.norm('GOV_MFA')[0], 'gov_mfa')

            async with await core.snap() as snap:
                guid0 = s_common.guid()
                name = '\u21f1\u21f2 Inc.'
                normname = '\u21f1\u21f2 inc.'
                altnames = ('altarrowname', 'otheraltarrow', )
                oprops = {
                    'loc': 'US.CA',
                    'name': name,
                    'names': altnames,
                    'alias': 'arrow',
                    'phone': '+15555555555',
                    'sic': '0119',
                    'naics': 541715,
                    'url': 'http://www.arrowinc.link',
                    'us:cage': '7qe71',
                    'founded': '2015',
                    'dissolved': '2019',
                }
                node = await snap.addNode('ou:org', guid0, oprops)
                self.eq(node.ndef[1], guid0),
                self.eq(node.get('loc'), 'us.ca')
                self.eq(node.get('name'), normname)
                self.eq(node.get('names'), altnames)
                self.eq(node.get('alias'), 'arrow')
                self.eq(node.get('phone'), '15555555555')
                self.eq(node.get('sic'), '0119')
                self.eq(node.get('naics'), '541715')
                self.eq(node.get('url'), 'http://www.arrowinc.link')
                self.eq(node.get('us:cage'), '7qe71')
                self.eq(node.get('founded'), 1420070400000)
                self.eq(node.get('dissolved'), 1546300800000)

                nodes = await snap.nodes('ou:name')
                self.sorteq([x.ndef[1] for x in nodes], (normname,) + altnames)

                nodes = await snap.nodes('ou:org:names*[=otheraltarrow]')
                self.len(1, nodes)

                opts = {'var': {'name': name}}
                nodes = await snap.nodes('ou:org:names*contains=$name', opts=opts)
                self.len(0, nodes)  # primary ou:org:name is not in ou:org:names

                person0 = s_common.guid()
                mprops = {
                    'title': 'Dancing Clown',
                    'start': '2001',
                    'end': '2010',
                }
                node = await snap.addNode('ou:member', (guid0, person0), mprops)
                self.eq(node.ndef[1], (guid0, person0))
                self.eq(node.get('title'), 'dancing clown')
                self.eq(node.get('start'), 978307200000)
                self.eq(node.get('end'), 1262304000000)

                # ou:suborg
                guid1 = s_common.guid()
                subprops = {
                    'perc': 50,
                    'current': True,
                }
                node = await snap.addNode('ou:suborg', (guid0, guid1), subprops)
                self.eq(node.ndef[1], (guid0, guid1))
                self.eq(node.get('perc'), 50)
                self.eq(node.get('current'), 1)

                await self.asyncraises(s_exc.BadTypeValu, node.set('perc', -1))
                await self.asyncraises(s_exc.BadTypeValu, node.set('perc', 101))

                # ou:user
                node = await snap.addNode('ou:user', (guid0, 'arrowman'))
                self.eq(node.ndef[1], (guid0, 'arrowman'))
                self.eq(node.get('org'), guid0)
                self.eq(node.get('user'), 'arrowman')

                # ou:hasalias
                node = await snap.addNode('ou:hasalias', (guid0, 'EVILCORP'))
                self.eq(node.ndef[1], (guid0, 'evilcorp'))
                self.eq(node.get('alias'), 'evilcorp')
                self.eq(node.get('org'), guid0)

                # ou:orgnet4
                node = await snap.addNode('ou:orgnet4', (guid0, ('192.168.1.1', '192.168.1.127')))
                self.eq(node.ndef[1], (guid0, (3232235777, 3232235903)))
                self.eq(node.get('net'), (3232235777, 3232235903))
                self.eq(node.get('org'), guid0)

                # ou:orgnet6
                node = await snap.addNode('ou:orgnet6', (guid0, ('fd00::1', 'fd00::127')))
                self.eq(node.ndef[1], (guid0, ('fd00::1', 'fd00::127')))
                self.eq(node.get('net'), ('fd00::1', 'fd00::127'))
                self.eq(node.get('org'), guid0)

                # ou:org:has
                node = await snap.addNode('ou:org:has', (guid0, ('test:str', 'pretty floral bonnet')))
                self.eq(node.ndef[1], (guid0, ('test:str', 'pretty floral bonnet')))
                self.eq(node.get('org'), guid0)
                self.eq(node.get('node'), ('test:str', 'pretty floral bonnet'))
                self.eq(node.get('node:form'), 'test:str')

                # ou:meet
                place0 = s_common.guid()
                m0 = s_common.guid()
                mprops = {
                    'name': 'Working Lunch',
                    'start': '201604011200',
                    'end': '201604011300',
                    'place': place0,
                }
                node = await snap.addNode('ou:meet', m0, mprops)
                self.eq(node.ndef[1], m0)
                self.eq(node.get('name'), 'working lunch')
                self.eq(node.get('start'), 1459512000000)
                self.eq(node.get('end'), 1459515600000)
                self.eq(node.get('place'), place0)

                mprops = {
                    'arrived': '201604011201',
                    'departed': '201604011259',
                }
                node = await snap.addNode('ou:meet:attendee', (m0, person0), mprops)
                self.eq(node.ndef[1], (m0, person0))
                self.eq(node.get('arrived'), 1459512060000)
                self.eq(node.get('departed'), 1459515540000)

                # ou:conference
                c0 = s_common.guid()
                cprops = {
                    'org': guid0,
                    'name': 'arrowcon 2018',
                    'base': 'arrowcon',
                    'start': '20180301',
                    'end': '20180303',
                    'place': place0,
                    'url': 'http://arrowcon.org/2018',
                }
                node = await snap.addNode('ou:conference', c0, cprops)
                self.eq(node.ndef[1], c0)
                self.eq(node.get('name'), 'arrowcon 2018')
                self.eq(node.get('base'), 'arrowcon')
                self.eq(node.get('org'), guid0)
                self.eq(node.get('start'), 1519862400000)
                self.eq(node.get('end'), 1520035200000)
                self.eq(node.get('place'), place0)
                self.eq(node.get('url'), 'http://arrowcon.org/2018')

                cprops = {
                    'arrived': '201803010800',
                    'departed': '201803021500',
                    'role:staff': False,
                    'role:speaker': True,
                    'roles': ['usher', 'coatcheck'],
                }
                node = await snap.addNode('ou:conference:attendee', (c0, person0), cprops)
                self.eq(node.ndef[1], (c0, person0))
                self.eq(node.get('arrived'), 1519891200000)
                self.eq(node.get('departed'), 1520002800000)
                self.eq(node.get('role:staff'), 0)
                self.eq(node.get('role:speaker'), 1)
                self.eq(node.get('roles'), ('usher', 'coatcheck'))

                # ou:conference:event
                confguid = c0

                con0 = s_common.guid()
                cprops = {
                    'org': guid0,
                    'name': 'Steve Rogers',
                    'title': 'The First Avenger',
                    'orgname': 'Avengers',
                    'user': 'cap',
                    'web:acct': ('twitter.com', 'captainamerica'),
                    'dob': '1918-07-04',
                    'url': 'https://captainamerica.com/',
                    'email': 'steve.rogers@gmail.com',
                    'email:work': 'cap@avengers.com',
                    'phone': '12345678910',
                    'phone:fax': '12345678910',
                    'phone:work': '12345678910',
                    'address': '222 Avenger Row, Washington, DCSan Francisco, CA, 22222, USA',
                }
                pscon = await snap.addNode('ps:contact', con0, cprops)

                c0 = s_common.guid()
                cprops = {
                    'conference': confguid,
                    'name': 'arrowcon 2018 dinner',
                    'desc': 'arrowcon dinner',
                    'start': '201803011900',
                    'end': '201803012200',
                    'contact': con0,
                    'place': place0,
                    'url': 'http://arrowcon.org/2018/dinner',
                }
                node = await snap.addNode('ou:conference:event', c0, cprops)
                self.eq(node.ndef[1], c0)
                self.eq(node.get('name'), 'arrowcon 2018 dinner')
                self.eq(node.get('desc'), 'arrowcon dinner')
                self.eq(node.get('conference'), confguid)
                self.eq(node.get('start'), 1519930800000)
                self.eq(node.get('end'), 1519941600000)
                self.eq(node.get('contact'), con0)
                self.eq(node.get('place'), place0)
                self.eq(node.get('url'), 'http://arrowcon.org/2018/dinner')

                cprops = {
                    'arrived': '201803011923',
                    'departed': '201803012300',
                    'roles': ['staff', 'speaker'],
                }
                node = await snap.addNode('ou:conference:event:attendee', (c0, person0), cprops)
                self.eq(node.ndef[1], (c0, person0))
                self.eq(node.get('arrived'), 1519932180000)
                self.eq(node.get('departed'), 1519945200000)
                self.eq(node.get('roles'), ('staff', 'speaker'))

    async def test_ou_code_prefixes(self):
        guid0 = s_common.guid()
        guid1 = s_common.guid()
        guid2 = s_common.guid()
        guid3 = s_common.guid()
        omap = {
            guid0: {'naics': '221121',
                    'sic': '0111'},
            guid1: {'naics': '221122',
                    'sic': '0112'},
            guid2: {'naics': '221113',
                    'sic': '2833'},
            guid3: {'naics': '221320',
                    'sic': '0134'}
        }
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                for g, props in omap.items():
                    await snap.addNode('ou:org', g, props)

                nodes = await snap.nodes('ou:org:sic^=01')
                self.len(3, nodes)

                nodes = await snap.nodes('ou:org:sic^=011')
                self.len(2, nodes)

                nodes = await snap.nodes('ou:org:naics^=22')
                self.len(4, nodes)

                nodes = await snap.nodes('ou:org:naics^=221')
                self.len(4, nodes)

                nodes = await snap.nodes('ou:org:naics^=2211')
                self.len(3, nodes)

                nodes = await snap.nodes('ou:org:naics^=22112')
                self.len(2, nodes)

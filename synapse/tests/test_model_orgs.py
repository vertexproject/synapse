import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class OuModelTest(s_t_utils.SynTest):

    async def test_ou_simple(self):
        async with self.getTestCore() as core:
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

            async with await core.snap() as snap:
                guid0 = s_common.guid()
                name = '\u21f1\u21f2 Inc.'
                normname = '\u21f1\u21f2 inc.'
                oprops = {
                    'loc': 'US.CA',
                    'name': name,
                    'alias': 'arrow',
                    'phone': '+15555555555',
                    'sic': '0119',
                    'naics': 541715,
                    'url': 'http://www.arrowinc.link',
                    'us:cage': '7qe71',
                    'founded': '2015',
                    'disolved': '2019',
                }
                node = await snap.addNode('ou:org', guid0, oprops)
                self.eq(node.ndef[1], guid0),
                self.eq(node.get('loc'), 'us.ca')
                self.eq(node.get('name'), normname)
                self.eq(node.get('alias'), 'arrow')
                self.eq(node.get('phone'), '15555555555')
                self.eq(node.get('sic'), '0119')
                self.eq(node.get('naics'), '541715')
                self.eq(node.get('url'), 'http://www.arrowinc.link')
                self.eq(node.get('us:cage'), '7qe71')
                self.eq(node.get('founded'), 1420070400000)
                self.eq(node.get('disolved'), 1546300800000)

                node = (await alist(snap.getNodesBy('ou:name', name)))[0]
                self.eq(node.ndef[1], normname)

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

                await self.asyncraises(s_exc.BadPropValu, node.set('perc', -1))
                await self.asyncraises(s_exc.BadPropValu, node.set('perc', 101))

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
                    'place': place0
                }
                node = await snap.addNode('ou:conference', c0, cprops)
                self.eq(node.ndef[1], c0)
                self.eq(node.get('name'), 'arrowcon 2018')
                self.eq(node.get('base'), 'arrowcon')
                self.eq(node.get('org'), guid0)
                self.eq(node.get('start'), 1519862400000)
                self.eq(node.get('end'), 1520035200000)
                self.eq(node.get('place'), place0)

                cprops = {
                    'arrived': '201803010800',
                    'departed': '201803021500',
                    'role:staff': False,
                    'role:speaker': True,
                }
                node = await snap.addNode('ou:conference:attendee', (c0, person0), cprops)
                self.eq(node.ndef[1], (c0, person0))
                self.eq(node.get('arrived'), 1519891200000)
                self.eq(node.get('departed'), 1520002800000)
                self.eq(node.get('role:staff'), 0)
                self.eq(node.get('role:speaker'), 1)

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
                nodes = await alist(snap.getNodesBy('ou:org:sic', '01', cmpr='^='))
                self.len(3, nodes)

                nodes = await alist(snap.getNodesBy('ou:org:sic', '011', cmpr='^='))
                self.len(2, nodes)

                nodes = await alist(snap.getNodesBy('ou:org:naics', '22', cmpr='^='))
                self.len(4, nodes)

                nodes = await alist(snap.getNodesBy('ou:org:naics', '221', cmpr='^='))
                self.len(4, nodes)

                nodes = await alist(snap.getNodesBy('ou:org:naics', '2211', cmpr='^='))
                self.len(3, nodes)

                nodes = await alist(snap.getNodesBy('ou:org:naics', '22112', cmpr='^='))
                self.len(2, nodes)

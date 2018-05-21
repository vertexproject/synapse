import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.common as s_test

# FIXME
# 1. ou:conference:name req prop

class OuModelTest(s_test.SynTest):

    def test_ou_simple(self):
        with self.getTestCore() as core:
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

            with core.snap(write=True) as snap:
                guid0 = s_common.guid()
                oprops = {
                    'loc': 'US.CA',
                    'name': '\u21f1\u21f2 Inc.',
                    'name:en': ' Arrow inc.',
                    'alias': 'arrow',
                    'phone': '+15555555555',
                    'sic': '0119',
                    'naics': 541715,
                    'url': 'http://www.arrowinc.link',
                    'us:cage': '7qe71'
                }
                node = snap.addNode('ou:org', guid0, oprops)
                self.eq(node.ndef[1], guid0),
                self.eq(node.get('loc'), 'us.ca')
                self.eq(node.get('name'), '\u21f1\u21f2 inc.')
                self.eq(node.get('name:en'), 'arrow inc.')
                self.eq(node.get('alias'), 'arrow')
                self.eq(node.get('phone'), '15555555555')
                self.eq(node.get('sic'), '0119')
                self.eq(node.get('naics'), '541715')
                self.eq(node.get('url'), 'http://www.arrowinc.link')
                self.eq(node.get('us:cage'), '7qe71')

                person0 = s_common.guid()
                mprops = {
                    'title': 'Dancing Clown',
                    'start': '2001',
                    'end': '2010',
                }
                node = snap.addNode('ou:member', (guid0, person0), mprops)
                self.eq(node.ndef[1], (guid0, person0))
                self.eq(node.get('title'), 'dancing clown')
                self.eq(node.get('start'), 978307200000)
                self.eq(node.get('end'), 1262304000000)

                # ou:suborg
                guid1 = s_common.guid()
                subprops = {
                    'perc': 50,
                    'current': True,
                    # Fixme - seen:min / seen:max
                }
                node = snap.addNode('ou:suborg', (guid0, guid1), subprops)
                self.eq(node.ndef[1], (guid0, guid1))
                self.eq(node.get('perc'), 50)
                self.eq(node.get('current'), 1)
                self.false(node.set('perc', -1))
                self.false(node.set('perc', 101))

                # ou:user
                node = snap.addNode('ou:user', (guid0, 'arrowman'))
                self.eq(node.ndef[1], (guid0, 'arrowman'))
                self.eq(node.get('org'), guid0)
                self.eq(node.get('user'), 'arrowman')

                # ou:haslias
                node = snap.addNode('ou:hasalias', (guid0, 'EVILCORP'))
                self.eq(node.ndef[1], (guid0, 'evilcorp'))
                self.eq(node.get('alias'), 'evilcorp')
                self.eq(node.get('org'), guid0)

                # ou:org:has
                # FIXME this should be a test form eventually
                node = snap.addNode('ou:org:has', (guid0, ('teststr', 'pretty floral bonnet')))
                self.eq(node.ndef[1], (guid0, ('teststr', 'pretty floral bonnet')))
                self.eq(node.get('org'), guid0)
                self.eq(node.get('node'), ('teststr', 'pretty floral bonnet'))
                self.eq(node.get('node:form'), 'teststr')
                # FIXME This is an autoadds test and should be tested elsewhere
                nodes = list(snap.getNodesBy('teststr', 'pretty floral bonnet'))
                self.len(1, nodes)
                # FIXME seen:min / seen:max

                # ou:meet
                m0 = s_common.guid()
                mprops = {
                    'name': 'Working Lunch',
                    'start': '201604011200',
                    'end': '201604011300',
                    # 'place': '', # FIXME geospatial
                }
                node = snap.addNode('ou:meet', m0, mprops)
                self.eq(node.ndef[1], m0)
                self.eq(node.get('name'), 'working lunch')
                self.eq(node.get('start'), 1459512000000)
                self.eq(node.get('end'), 1459515600000)

                mprops = {
                    'arrived': '201604011201',
                    'departed': '201604011259',
                }
                node = snap.addNode('ou:meet:attendee', (m0, person0), mprops)
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
                    # 'place': '', # FIXME geospatial
                }
                node = snap.addNode('ou:conference', c0, cprops)
                self.eq(node.ndef[1], c0)
                self.eq(node.get('name'), 'arrowcon 2018')
                self.eq(node.get('base'), 'arrowcon')
                self.eq(node.get('org'), guid0)
                self.eq(node.get('start'), 1519862400000)
                self.eq(node.get('end'), 1520035200000)

                cprops = {
                    'arrived': '201803010800',
                    'departed': '201803021500',
                    'role:staff': False,
                    'role:speaker': True,
                }
                node = snap.addNode('ou:conference:attendee', (c0, person0), cprops)
                self.eq(node.ndef[1], (c0, person0))
                self.eq(node.get('arrived'), 1519891200000)
                self.eq(node.get('departed'), 1520002800000)
                self.eq(node.get('role:staff'), 0)
                self.eq(node.get('role:speaker'), 1)

    def test_ou_code_prefixes(self):
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
        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                for g, props in omap.items():
                    node = snap.addNode('ou:org', g, props)
                nodes = list(snap.getNodesBy('ou:org:sic', '01', cmpr='^='))
                self.len(3, nodes)

                nodes = list(snap.getNodesBy('ou:org:sic', '011', cmpr='^='))
                self.len(2, nodes)

                nodes = list(snap.getNodesBy('ou:org:naics', '22', cmpr='^='))
                self.len(4, nodes)

                nodes = list(snap.getNodesBy('ou:org:naics', '221', cmpr='^='))
                self.len(4, nodes)

                nodes = list(snap.getNodesBy('ou:org:naics', '2211', cmpr='^='))
                self.len(3, nodes)

                nodes = list(snap.getNodesBy('ou:org:naics', '22112', cmpr='^='))
                self.len(2, nodes)

class FIXME:

    def test_model_orgs_seed_alias(self):
        with self.getRamCore() as core:

            node0 = core.formTufoByProp('ou:org:alias', 'wewtcorp', name='The Woot Corp')

            self.eq(node0[1].get('ou:org:alias'), 'wewtcorp')
            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            node1 = core.formTufoByProp('ou:org:alias', 'wewtcorp')

            self.eq(node0[0], node1[0])

    def test_model_orgs_seed_name(self):
        with self.getRamCore() as core:

            node0 = core.formTufoByProp('ou:org:name', 'The Woot Corp')
            node1 = core.formTufoByProp('ou:org:name', 'the woot corp')

            self.eq(node0[1].get('ou:org:name'), 'the woot corp')

            self.eq(node0[0], node1[0])

    def test_model_orgs_oumember(self):
        with self.getRamCore() as core:
            pnode = core.formTufoByProp('ps:person', '*', name='grey, robert')
            _, pprop = s_tufo.ndef(pnode)

            onode = core.formTufoByProp('ou:org:name', 'derry sanitation corp')
            _, oprop = s_tufo.ndef(onode)

            mnode = core.formTufoByProp('ou:member',
                                        {'org': oprop, 'person': pprop},
                                        **{'start': '2017',
                                           'end': '2018',
                                           'title': 'Dancing Clown'})
            self.nn(mnode)
            _, mpprop = s_tufo.ndef(mnode)
            props = s_tufo.props(mnode)
            self.eq(props.get('org'), oprop)
            self.eq(props.get('person'), pprop)
            self.eq(props.get('end'), core.getTypeNorm('time', '2018')[0])
            self.eq(props.get('start'), core.getTypeNorm('time', '2017')[0])
            self.eq(props.get('title'), 'dancing clown')

            # We can traverse across the ou:member node
            nodes = core.eval('ps:person=%s -> ou:member:person :org -> ou:org' % pprop)
            self.len(1, nodes)
            self.eq(oprop, nodes[0][1].get('ou:org'))

            nodes = core.eval('ou:org=%s -> ou:member:org :person -> ps:person' % oprop)
            self.len(1, nodes)
            self.eq(pprop, nodes[0][1].get('ps:person'))

    def test_model_org_meeting(self):

        with self.getRamCore() as core:

            plac = s_common.guid()
            pers = s_common.guid()

            props = {
                'name': 'woot woot',
                'place': plac,
                'start': '2016 12 17 14:30',
                'end': '2016 12 17 15:00',
            }

            meet = core.formTufoByProp('ou:meet', '*', **props)

            self.eq(meet[1].get('ou:meet:name'), 'woot woot')
            self.eq(meet[1].get('ou:meet:start'), 1481985000000)
            self.eq(meet[1].get('ou:meet:end'), 1481986800000)
            self.eq(meet[1].get('ou:meet:place'), plac)

            iden = meet[1].get('ou:meet')

            props = {
                'arrived': '2016 12 17 14:33',
                'departed': '2016 12 17 15:13',
            }
            atnd = core.formTufoByProp('ou:meet:attendee', (iden, pers), **props)

            self.eq(atnd[1].get('ou:meet:attendee:meet'), iden)
            self.eq(atnd[1].get('ou:meet:attendee:person'), pers)
            self.eq(atnd[1].get('ou:meet:attendee:arrived'), 1481985180000)
            self.eq(atnd[1].get('ou:meet:attendee:departed'), 1481987580000)

            props = {
                'base': 'woot',
                'name': 'woot 2016',
                'place': plac,
                'start': '2016 12 17 14:30',
                'end': '2016 12 17 15:00',
            }
            conf = core.formTufoByProp('ou:conference', '*', **props)

            iden = conf[1].get('ou:conference')

            self.eq(conf[1].get('ou:conference:base'), 'woot')
            self.eq(conf[1].get('ou:conference:name'), 'woot 2016')
            self.eq(conf[1].get('ou:conference:place'), plac)
            self.eq(conf[1].get('ou:conference:start'), 1481985000000)
            self.eq(conf[1].get('ou:conference:end'), 1481986800000)

            props = {
                'arrived': '2016 12 17 14:33',
                'departed': '2016 12 17 15:13',
                'role:staff': 1,
                'role:speaker': 0,
            }
            atnd = core.formTufoByProp('ou:conference:attendee', (iden, pers), **props)

            self.eq(atnd[1].get('ou:conference:attendee:conference'), iden)
            self.eq(atnd[1].get('ou:conference:attendee:person'), pers)
            self.eq(atnd[1].get('ou:conference:attendee:arrived'), 1481985180000)
            self.eq(atnd[1].get('ou:conference:attendee:departed'), 1481987580000)
            self.eq(atnd[1].get('ou:conference:attendee:role:staff'), 1)
            self.eq(atnd[1].get('ou:conference:attendee:role:speaker'), 0)

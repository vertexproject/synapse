import synapse.exc as s_exc
import synapse.common as s_common

from synapse.tests.common import *

class InetModelTest(SynTest):

    # Form Tests ===================================================================================
    def test_forms_ipv4(self):
        # FIXME add latlong later
        formname = 'inet:ipv4'
        valu_str = '1.2.3.4'
        valu_int = 16909060
        input_props = {'asn': 3, 'loc': 'us', 'type': 'cool'}
        expected_props = {'asn': 3, 'loc': 'us', 'type': 'cool'}
        expected_ndef = (formname, valu_int)

        with self.getTestCore() as core:
            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu_str, props=input_props)

            self.eq(node.ndef, expected_ndef)
            self.eq(node.props, expected_props)

    def test_forms_fqdn(self):
        formname = 'inet:fqdn'
        valu = 'api.vertex.link'
        expected_ndef = (formname, valu)

        # props: domain host issuffix iszone zone
        with self.getTestCore() as core:

            # Demonstrate cascading formation
            expected_props = {'created': 0, 'domain': 'vertex.link', 'expires': 1, 'host': 'api', 'issuffix': 0,
                'iszone': 0, 'updated': 2, 'zone': 'vertex.link'}
            with core.xact(write=True) as xact:
                node = xact.addNode(formname, valu, props={'created': 0, 'expires': 1, 'updated': 2})
            self.eq(node.ndef, expected_ndef)
            self.eq(node.props, expected_props)

            nvalu = expected_props['domain']
            expected_ndef = (formname, nvalu)
            expected_props = {'domain': 'link', 'host': 'vertex', 'issuffix': 0, 'iszone': 1, 'zone': 'vertex.link'}
            with core.xact() as xact:
                node = xact.getNodeByNdef((formname, nvalu))
            self.eq(node.ndef, expected_ndef)
            self.eq(node.props, expected_props)

            nvalu = expected_props['domain']
            expected_ndef = (formname, nvalu)
            expected_props = {'host': 'link', 'issuffix': 1, 'iszone': 0}
            with core.xact() as xact:
                node = xact.getNodeByNdef((formname, nvalu))
            self.eq(node.ndef, expected_ndef)
            self.eq(node.props, expected_props)

            # Demonstrate wildcard
            with core.xact() as xact:
                self.len(3, list(xact.getNodesBy(formname, '*')))
                self.len(2, list(xact.getNodesBy(formname, '*.link')))
                self.len(1, list(xact.getNodesBy(formname, '*.vertex.link')))
                badgen = xact.getNodesBy(formname, 'api.*.link')
                self.raises(s_exc.BadLiftValu, list, badgen)

    def test_forms_fqdn_suffix(self):
        formname = 'inet:fqdn'
        def iszone(node):
            self.true(node.props.get('iszone') == 1 and node.props.get('issuffix') == 0)

        def issuffix(node):
            self.true(node.props.get('issuffix') == 1 and node.props.get('iszone') == 0)

        def isboth(node):
            self.true(node.props.get('iszone') == 1 and node.props.get('issuffix') == 1)

        def isneither(node):
            self.true(node.props.get('iszone') == 0 and node.props.get('issuffix') == 0)

        with self.getTestCore() as core:
            with core.xact(write=True) as xact:

                # Create some nodes and demonstrate zone/suffix behavior
                # Only FQDNs of the lowest level should be suffix
                # Only FQDNs whose domains are suffixes should be zones
                n0 = xact.addNode(formname, 'abc.vertex.link')
                n1 = xact.addNode(formname, 'def.vertex.link')
                n2 = xact.addNode(formname, 'g.def.vertex.link')
                n1 = xact.addNode(formname, 'def.vertex.link')  # form again to show g. should not make this a zone
                n3 = xact.getNodeByNdef((formname, 'vertex.link'))
                n4 = xact.getNodeByNdef((formname, 'link'))
                isneither(n0)
                isneither(n1)
                isneither(n2)
                iszone(n3)     # vertex.link should be a zone
                issuffix(n4)   # link should be a suffix

                # Make one of the FQDNs a suffix and make sure its children become zones
                n3 = xact.addNode(formname, 'vertex.link', props={'issuffix': True})
                isboth(n3)     # vertex.link should now be both because we made it a suffix
                n0 = xact.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = xact.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = xact.getNodeByNdef((formname, 'g.def.vertex.link'))
                iszone(n0)     # now a zone because vertex.link is a suffix
                iszone(n1)     # now a zone because vertex.link is a suffix
                isneither(n2)  # still neither as parent is not a suffix

                # Remove the FQDN's suffix status and make sure its children lose zone status
                n3 = xact.addNode(formname, 'vertex.link', props={'issuffix': False})
                iszone(n3)     # vertex.link should now be a zone becuase we removed its suffix status
                n0 = xact.getNodeByNdef((formname, 'abc.vertex.link'))
                n1 = xact.getNodeByNdef((formname, 'def.vertex.link'))
                n2 = xact.getNodeByNdef((formname, 'g.def.vertex.link'))
                n4 = xact.getNodeByNdef((formname, 'link'))
                isneither(n0)  # loses zone status
                isneither(n1)  # loses zone status
                isneither(n2)  # stays the same
                issuffix(n4)   # stays the same

    # Type Tests ===================================================================================
    def test_types_fqdn(self):
        with self.getTestCore() as core:
            t = core.model.type('inet:fqdn')

            fqdn = 'example.Vertex.link'
            expected = ('example.vertex.link', {'subs': {'host': 'example', 'domain': 'vertex.link'}})
            self.eq(t.norm(fqdn), expected)
            self.raises(s_exc.BadTypeValu, t.norm, '!@#$%')

            # Demonstrate Valid IDNA
            fqdn = 'tèst.èxamplè.link'
            ex_fqdn = 'xn--tst-6la.xn--xampl-3raf.link'
            expected = (ex_fqdn, {'subs': {'domain': 'xn--xampl-3raf.link', 'host': 'xn--tst-6la'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(t.repr(ex_fqdn), fqdn)  # Calling repr on IDNA encoded domain should result in the unicode
            self.raises(UnicodeDecodeError, t.repr, fqdn)  # Can't repr unicode domain

            # Demonstrate Invalid IDNA
            fqdn = 'xn--lskfjaslkdfjaslfj.link'
            expected = (fqdn, {'subs': {'host': fqdn.split('.')[0], 'domain': 'link'}})
            self.eq(t.norm(fqdn), expected)
            self.eq(t.repr(fqdn), fqdn)  # UnicodeError raised and caught

    def test_types_ipv4(self):
        # FIXME add latlong later
        with self.getTestCore() as core:
            t = core.model.type('inet:ipv4')
            ip_int = 16909060
            ip_str = '1.2.3.4'
            ip_str_enfanged = '1[.]2[.]3[.]4'

            self.eq(t.norm(ip_int), (ip_int, {}))
            self.eq(t.norm(ip_str), (ip_int, {}))
            self.eq(t.norm(ip_str_enfanged), (ip_int, {}))
            self.eq(t.repr(ip_int), ip_str)

            # Demonstrate wrap-around
            self.eq(t.norm(0x00000000 - 1), (2**32 - 1, {}))
            self.eq(t.norm(0xFFFFFFFF + 1), (0, {}))


class FIXME:

    def test_forms_url(self):
        # FIXME implement when porting the rest of the inet model
        pass

        '''
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:url', 'HTTP://visi:hehe@www.vertex.link:9999/')
            self.eq(node[1].get('inet:url:port'), 9999)
            self.eq(node[1].get('inet:url:user'), 'visi')
            self.eq(node[1].get('inet:url:passwd'), 'hehe')
            self.eq(node[1].get('inet:url:fqdn'), 'www.vertex.link')

            node = core.formTufoByProp('inet:url', 'HTTP://www.vertex.link/')
            self.eq(node[1].get('inet:url:port'), 80)

            node = core.formTufoByProp('inet:url', 'HTTP://1.2.3.4/')
            self.eq(node[1].get('inet:url:ipv4'), 0x01020304)
        '''

    def test_model_inet_srv4_types(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:tcp4', '8.8.8.8:80')
            form, pprop = s_tufo.ndef(t0)
            self.eq(pprop, 8830587502672)
            self.eq(t0[1].get('inet:tcp4:port'), 80)
            self.eq(t0[1].get('inet:tcp4:ipv4'), core.getTypeNorm('inet:ipv4', '8.8.8.8')[0])

            # 1.2.3.4:8443
            t1 = core.formTufoByProp('inet:tcp4', 1108152164603)
            self.eq(t1[1].get('inet:tcp4:port'), 8443)
            self.eq(t1[1].get('inet:tcp4:ipv4'), core.getTypeNorm('inet:ipv4', '1.2.3.4')[0])

            t2 = core.formTufoByProp('inet:udp4', '8.8.8.8:80')
            form, pprop = s_tufo.ndef(t2)
            self.eq(pprop, 8830587502672)
            self.eq(t2[1].get('inet:udp4:port'), 80)
            self.eq(t2[1].get('inet:udp4:ipv4'), core.getTypeNorm('inet:ipv4', '8.8.8.8')[0])

            # 1.2.3.4:8443
            t3 = core.formTufoByProp('inet:udp4', 1108152164603)
            self.eq(t3[1].get('inet:udp4:port'), 8443)
            self.eq(t3[1].get('inet:udp4:ipv4'), core.getTypeNorm('inet:ipv4', '1.2.3.4')[0])

            # 1.2.3.4:8443
            t4 = core.formTufoByProp('inet:udp4', '1108152164603')
            self.eq(t4[1].get('inet:udp4:port'), 8443)
            self.eq(t4[1].get('inet:udp4:ipv4'), core.getTypeNorm('inet:ipv4', '1.2.3.4')[0])

            # Ensure boundaries are observed
            for i in ['0', 0, '0.0.0.0:0']:
                valu, subs = core.getTypeNorm('inet:srv4', i)
                self.eq(valu, 0)
                self.eq(subs.get('port'), 0)
                self.eq(subs.get('ipv4'), 0)

            for i in ['281474976710655', 281474976710655, '255.255.255.255:65535']:
                valu, subs = core.getTypeNorm('inet:srv4', i)
                self.eq(valu, 281474976710655)
                self.eq(subs.get('port'), 0xFFFF)
                self.eq(subs.get('ipv4'), 0xFFFFFFFF)

            # Repr works as expected
            self.eq(core.getTypeRepr('inet:srv4', 0), '0.0.0.0:0')
            self.eq(core.getTypeRepr('inet:srv4', 1108152164603), '1.2.3.4:8443')
            self.eq(core.getTypeRepr('inet:srv4', 281474976710655), '255.255.255.255:65535')

            # Ensure bad input fails
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '281474976710656')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', 281474976710656)
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '255.255.255.255:65536')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '255.255.255.255:-1')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', -1)
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '-1')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', 'ruh roh')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:srv4', '1.2.3.4:8080:9090')

    def test_model_inet_srv6_types(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:tcp6', '[0:0:0:0:0:0:0:1]:80')
            form, pprop = s_tufo.ndef(t0)
            self.eq(pprop, '[::1]:80')
            self.eq(t0[1].get('inet:tcp6:port'), 80)
            self.eq(t0[1].get('inet:tcp6:ipv6'), '::1')

            t1 = core.formTufoByProp('inet:tcp6', '[0:0:0:0:0:3:2:1]:443')
            form, pprop = s_tufo.ndef(t1)
            self.eq(pprop, '[::3:2:1]:443')
            self.eq(t1[1].get('inet:tcp6:port'), 443)
            self.eq(t1[1].get('inet:tcp6:ipv6'), '::3:2:1')

            t2 = core.formTufoByProp('inet:udp6', '[0:0:0:0:0:3:2:1]:5000')
            form, pprop = s_tufo.ndef(t2)
            self.eq(pprop, '[::3:2:1]:5000')
            self.eq(t2[1].get('inet:udp6:port'), 5000)
            self.eq(t2[1].get('inet:udp6:ipv6'), '::3:2:1')

            self.eq(core.getTypeRepr('inet:tcp6', '[0:0:0:0:0:0:0:1]:80'), '[::1]:80')
            self.eq(core.getTypeRepr('inet:tcp6', '[::1]:80'), '[::1]:80')
            self.eq(core.getTypeRepr('inet:tcp6', '[0:0:0:0:0:3:2:1]:5000'), '[::3:2:1]:5000')

    def test_model_inet_cast_defang(self):
        with self.getRamCore() as core:
            self.eq(core.getTypeCast('inet:defang', '1[.]2[.]3[.]4'), '1.2.3.4')

    def test_model_inet_whoisemail(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:whois:regmail', ('WOOT.COM', 'visi@vertex.LINK'))
            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.nn(core.getTufoByProp('inet:email', 'visi@vertex.link'))
            self.eq(node[1].get('inet:whois:regmail:email'), 'visi@vertex.link')
            self.eq(node[1].get('inet:whois:regmail:fqdn'), 'woot.com')

    def test_model_inet_url_fields(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:url', 'HTTP://visi:hehe@www.vertex.link:9999/')
            self.eq(node[1].get('inet:url:port'), 9999)
            self.eq(node[1].get('inet:url:user'), 'visi')
            self.eq(node[1].get('inet:url:passwd'), 'hehe')
            self.eq(node[1].get('inet:url:fqdn'), 'www.vertex.link')

            node = core.formTufoByProp('inet:url', 'HTTP://www.vertex.link/')
            self.eq(node[1].get('inet:url:port'), 80)

            node = core.formTufoByProp('inet:url', 'HTTP://1.2.3.4/')
            self.eq(node[1].get('inet:url:ipv4'), 0x01020304)

    def test_model_inet_web_acct(self):

        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:web:acct', 'vertex.link/person1',
                                     **{'name': 'ካሳር',
                                        'name:en': 'caesar',
                                        'realname': 'Брут',    # uppercased Cyrllic
                                        'realname:en': 'brutus',
                                        })
            self.eq(t0[1].get('inet:web:acct'), 'vertex.link/person1')
            self.eq(t0[1].get('inet:web:acct:site'), 'vertex.link')
            self.eq(t0[1].get('inet:web:acct:user'), 'person1')
            t0 = core.setTufoProp(t0, 'loc', 'HAHA')
            self.eq(t0[1].get('inet:web:acct:loc'), 'haha')
            self.eq(t0[1].get('inet:web:acct:name'), 'ካሳር')
            self.eq(t0[1].get('inet:web:acct:name:en'), 'caesar')
            self.eq(t0[1].get('inet:web:acct:realname'), 'брут')  # lowercased Cyrllic
            self.eq(t0[1].get('inet:web:acct:realname:en'), 'brutus')

    def test_model_inet_web_post(self):

        with self.getRamCore() as core:
            node0 = core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'knock knock'), time='20141217010101')
            iden = node0[1].get('inet:web:post')

            node1 = core.formTufoByProp('inet:web:post', ('vertex.link/visi', 'whos there'),
                                        time='20141217010102', replyto=iden)

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))

            self.eq(node0[1].get('inet:web:post:acct:user'), 'visi')
            self.eq(node1[1].get('inet:web:post:acct:user'), 'visi')

            self.eq(node0[1].get('inet:web:post:acct:site'), 'vertex.link')
            self.eq(node1[1].get('inet:web:post:acct:site'), 'vertex.link')

            self.eq(node0[1].get('inet:web:post'), node1[1].get('inet:web:post:replyto'))
            self.none(node0[1].get('inet:web:post:repost'))
            self.none(node1[1].get('inet:web:post:repost'))

            repost = node1[1].get('inet:web:post')
            node2 = core.formTufoByProp('inet:web:post', ('vertex.link/pennywise', 'whos there'),
                                        time='201710091541', repost=repost)
            self.eq(node2[1].get('inet:web:post:acct'), 'vertex.link/pennywise')
            self.eq(node2[1].get('inet:web:post:text'), 'whos there')
            self.eq(node2[1].get('inet:web:post:repost'), repost)
            self.none(node2[1].get('inet:web:replyto'))

    def test_model_inet_postref(self):
        with self.getRamCore() as core:

            fnod = core.formTufoByProp('file:bytes', 'd41d8cd98f00b204e9800998ecf8427e')
            pnod = core.formTufoByProp('inet:web:post', ('vertex.link/user1', 'txt about a file'))

            fiden = fnod[1].get('file:bytes')
            piden = pnod[1].get('inet:web:post')

            pr0 = core.formTufoByProp('inet:web:postref', (piden, ('file:bytes', fiden)))
            pr1 = core.formTufoByProp('inet:web:postref', '(%s,file:bytes=%s)' % (piden, fiden))

            self.eq(pr0[0], pr1[0])
            self.eq(pr0[1].get('inet:web:postref:post'), piden)
            self.eq(pr0[1].get('inet:web:postref:xref'), 'file:bytes=' + fiden)
            self.eq(pr0[1].get('inet:web:postref:xref:prop'), 'file:bytes')
            self.eq(pr0[1].get('inet:web:postref:xref:strval'), fiden)
            self.eq(pr0[1].get('inet:web:postref:xref:intval'), None)

    def test_model_inet_web_mesg(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:web:mesg', ('VERTEX.link/visi', 'vertex.LINK/hehe', '20501217'), text='hehe haha')
            self.nn(node)
            self.eq(node[1].get('inet:web:mesg:from'), 'vertex.link/visi')
            self.eq(node[1].get('inet:web:mesg:to'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:web:mesg:time'), 2554848000000)
            self.eq(node[1].get('inet:web:mesg:text'), 'hehe haha')

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/hehe'))

    def test_model_inet_web_memb(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:web:memb', ('VERTEX.link/visi', 'vertex.LINK/kenshoto'), joined='20501217')

            self.nn(node)

            self.eq(node[1].get('inet:web:memb:joined'), 2554848000000)
            self.eq(node[1].get('inet:web:memb:acct'), 'vertex.link/visi')
            self.eq(node[1].get('inet:web:memb:group'), 'vertex.link/kenshoto')

            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/visi'))
            self.nn(core.getTufoByProp('inet:web:group', 'vertex.link/kenshoto'))

    def test_model_inet_web_group(self):
        with self.getRamCore() as core:
            from pprint import pprint
            iden = guid()
            node = core.formTufoByProp('inet:web:group',
                                       ('vertex.link', '1234'),
                                       **{'name': 'brjálaður muffins',
                                          'name:en': 'crazy cupcakes',
                                          'url': 'http://vertex.link/g/1234',
                                          'desc': 'Crazy cupcakes players union',
                                          'avatar': iden,
                                          'webpage': 'http://muffinman.com/hehe',
                                          'loc': 'Reykjavík',
                                          'latlong': '64.0788707,-21.8369301',
                                          'signup': '2016',
                                          'signup:ipv4': '1.2.3.4',
                                          'signup:ipv6': '0:0:0:0:0:0:0:1',
                                          'seen:min': '2016',
                                          'seen:max': '2018'
                                          })
            self.nn(node)
            _, pprop = s_tufo.ndef(node)
            self.eq(pprop, 'vertex.link/1234')
            props = s_tufo.props(node)
            self.eq(props.get('avatar'), iden)
            self.eq(props.get('desc'), 'Crazy cupcakes players union')
            self.eq(props.get('id'), '1234')
            self.eq(props.get('latlong'), '64.0788707,-21.8369301')
            self.eq(props.get('loc'), 'reykjavík')
            self.eq(props.get('name'), 'brjálaður muffins')
            self.eq(props.get('name:en'), 'crazy cupcakes')
            self.eq(props.get('seen:max'), 1514764800000,)
            self.eq(props.get('seen:min'), 1451606400000,)
            self.eq(props.get('signup'), 1451606400000,)
            self.eq(props.get('signup:ipv4'), 16909060)
            self.eq(props.get('signup:ipv6'), '::1')
            self.eq(props.get('site'), 'vertex.link')
            self.eq(props.get('url'), 'http://vertex.link/g/1234')
            self.eq(props.get('webpage'), 'http://muffinman.com/hehe')
            # Validate autoadds
            self.nn(core.getTufoByProp('inet:group', '1234'))
            self.nn(core.getTufoByProp('inet:group', 'crazy cupcakes'))
            self.nn(core.getTufoByProp('inet:group', 'brjálaður muffins'))
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core.getTufoByProp('inet:fqdn', 'muffinman.com'))
            self.nn(core.getTufoByProp('file:bytes', iden))
            self.nn(core.getTufoByProp('inet:ipv4', '1.2.3.4'))
            self.nn(core.getTufoByProp('inet:ipv6', '::1'))

    def test_model_inet_web_follows(self):

        with self.getRamCore() as core:

            props = {'seen:min': '20501217', 'seen:max': '20501217'}
            node = core.formTufoByProp('inet:web:follows', ('VERTEX.link/visi', 'vertex.LINK/hehe'), **props)

            self.nn(node)
            self.eq(node[1].get('inet:web:follows:follower'), 'vertex.link/visi')
            self.eq(node[1].get('inet:web:follows:followee'), 'vertex.link/hehe')
            self.eq(node[1].get('inet:web:follows:seen:min'), 2554848000000)
            self.eq(node[1].get('inet:web:follows:seen:max'), 2554848000000)

    def test_model_inet_ipv4_raise(self):
        with self.getRamCore() as core:
            self.raises(BadTypeValu, core.formTufoByProp, 'inet:ipv4', 'lolololololol')

    def test_model_inet_urlfile(self):
        with self.getRamCore() as core:

            url = 'HTTP://visi:hehe@www.vertex.link:9999/'
            fguid = 32 * 'a'
            node = core.formTufoByProp('inet:urlfile', (url, fguid), **{'seen:min': 0, 'seen:max': 1})

            self.eq(node[1].get('inet:urlfile:file'), 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
            self.eq(node[1].get('inet:urlfile:url'), 'http://visi:hehe@www.vertex.link:9999/')
            self.eq(node[1].get('inet:urlfile:seen:min'), 0)
            self.eq(node[1].get('inet:urlfile:seen:max'), 1)

            self.none(node[1].get('inet:urlfile:url:port'))
            self.none(node[1].get('inet:urlfile:url:proto'))
            self.none(node[1].get('inet:urlfile:url:user'))
            self.none(node[1].get('inet:urlfile:url:passwd'))

    def test_model_whois_contact(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:whois:contact', '(woot.com@20501217,admin)')

            self.eq(len(core.eval('inet:fqdn="woot.com"')), 1)
            self.eq(len(core.eval('inet:whois:rec="woot.com@20501217"')), 1)
            self.eq(len(core.eval('inet:whois:contact:rec="woot.com@20501217"')), 1)

            props = {'url': 'http://woot.com/hehe', 'whois:fqdn': 'blah.com'}
            node = core.formTufoByProp('inet:whois:contact', ('woot.com@2015', 'registrar'), **props)
            self.eq(node[1].get('inet:whois:contact:url'), 'http://woot.com/hehe')
            self.eq(node[1].get('inet:whois:contact:whois:fqdn'), 'blah.com')

            self.nn(core.getTufoByProp('inet:fqdn', 'blah.com'))
            self.nn(core.getTufoByProp('inet:url', 'http://woot.com/hehe'))

    def test_model_inet_whois_recns(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:whois:rec', 'woot.com@20501217')
            form, pprop = s_tufo.ndef(node)
            node = core.formTufoByProp('inet:whois:recns', ['ns1.woot.com', pprop])
            self.eq(node[1].get('inet:whois:recns:ns'), 'ns1.woot.com')
            self.eq(node[1].get('inet:whois:recns:rec'), pprop)
            self.eq(node[1].get('inet:whois:recns:rec:fqdn'), 'woot.com')
            self.eq(node[1].get('inet:whois:recns:rec:asof'), 2554848000000)
            nodes = core.eval('inet:whois:recns:rec:fqdn=woot.com')
            self.eq(node[0], nodes[0][0])
            nodes = core.eval('inet:whois:rec:fqdn=woot.com inet:whois:rec->inet:whois:recns:rec')
            self.eq(len(nodes), 1)
            self.eq(node[0], nodes[0][0])

    def test_model_inet_web_logon(self):

        with self.getRamCore() as core:
            tick = now()

            t0 = core.formTufoByProp('inet:web:logon', '*', acct='vertex.link/pennywise', time=tick)
            self.nn(t0)

            self.eq(t0[1].get('inet:web:logon:time'), tick)
            self.eq(t0[1].get('inet:web:logon:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:logon:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:logon:acct:site'), 'vertex.link')

            # Pivot from an inet:web:acct to the inet:web:logon forms via storm
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise'))
            nodes = core.eval('inet:web:acct=vertex.link/pennywise inet:web:acct -> inet:web:logon:acct')
            self.eq(len(nodes), 1)

            t0 = core.setTufoProps(t0, ipv4=0x01020304, logout=tick + 1, ipv6='0:0:0:0:0:0:0:1')
            self.eq(t0[1].get('inet:web:logon:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:web:logon:logout'), tick + 1)
            self.eq(t0[1].get('inet:web:logon:logout') - t0[1].get('inet:web:logon:time'), 1)
            self.eq(t0[1].get('inet:web:logon:ipv6'), '::1')

    def test_model_inet_web_action(self):

        with self.getRamCore() as core:
            tick = now()

            t0 = core.formTufoByProp('inet:web:action', '*', act='didathing', acct='vertex.link/pennywise', time=tick)
            self.nn(t0)

            self.eq(t0[1].get('inet:web:action:time'), tick)
            self.eq(t0[1].get('inet:web:action:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:action:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:action:acct:site'), 'vertex.link')
            self.eq(t0[1].get('inet:web:action:act'), 'didathing')

            # Pivot from an inet:web:acct to the inet:web:action forms via storm
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise'))
            nodes = core.eval('inet:web:acct=vertex.link/pennywise inet:web:acct -> inet:web:action:acct')
            self.eq(len(nodes), 1)

            t0 = core.setTufoProps(t0, ipv4=0x01020304, ipv6='0:0:0:0:0:0:0:1', acct='vertex.link/user2')
            self.eq(t0[1].get('inet:web:action:ipv4'), 0x01020304)
            self.eq(t0[1].get('inet:web:action:ipv6'), '::1')
            self.eq(t0[1].get('inet:web:action:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:action:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:action:acct:site'), 'vertex.link')

            d = {'key': 1, 'valu': ['oh', 'my']}
            t0 = core.setTufoProps(t0, info=d)
            self.eq(json.loads(t0[1].get('inet:web:action:info')), d)

            self.raises(PropNotFound, core.formTufoByProp, 'inet:web:action', '*', acct='vertex.link/pennywise', time=tick)
            self.raises(PropNotFound, core.formTufoByProp, 'inet:web:action', '*', act='didathing', time=tick)

    def test_model_inet_web_actref(self):
        with self.getRamCore() as core:

            fnod = core.formTufoByProp('file:bytes', 'd41d8cd98f00b204e9800998ecf8427e')
            anod = core.formTufoByProp('inet:web:action', '*', act='laughed', acct='vertex.link/user1')

            fiden = fnod[1].get('file:bytes')
            aiden = anod[1].get('inet:web:action')

            ar0 = core.formTufoByProp('inet:web:actref', (aiden, ('file:bytes', fiden)))
            ar1 = core.formTufoByProp('inet:web:actref', '(%s,file:bytes=%s)' % (aiden, fiden))

            self.eq(ar0[0], ar1[0])
            self.eq(ar0[1].get('inet:web:actref:act'), aiden)
            self.eq(ar0[1].get('inet:web:actref:xref'), 'file:bytes=' + fiden)
            self.eq(ar0[1].get('inet:web:actref:xref:prop'), 'file:bytes')
            self.eq(ar0[1].get('inet:web:actref:xref:strval'), fiden)
            self.eq(ar0[1].get('inet:web:actref:xref:intval'), None)

    def test_model_inet_chprofile(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:web:chprofile', '*', acct='vertex.link/pennywise', ipv4='1.2.3.4',
                                     pv='inet:web:acct:name=bob gray', time='201710020800')
            self.eq(t0[1].get('inet:web:chprofile:acct'), 'vertex.link/pennywise')
            self.eq(t0[1].get('inet:web:chprofile:acct:site'), 'vertex.link')
            self.eq(t0[1].get('inet:web:chprofile:acct:user'), 'pennywise')
            self.eq(t0[1].get('inet:web:chprofile:ipv4'), 0x01020304)
            self.none(t0[1].get('inet:web:chprofile:acct:ipv6'))
            self.eq(t0[1].get('inet:web:chprofile:time'), 1506931200000)
            self.eq(t0[1].get('inet:web:chprofile:pv'), 'inet:web:acct:name=bob gray')
            self.eq(t0[1].get('inet:web:chprofile:pv:prop'), 'inet:web:acct:name')
            self.eq(t0[1].get('inet:web:chprofile:pv:strval'), 'bob gray')
            self.none(t0[1].get('inet:web:chprofile:pv:intval'))

            t1 = core.formTufoByProp('inet:web:chprofile', '*', acct='vertex.link/pennywise', ipv4='1.2.3.4',
                                     pv='inet:web:acct:seen:min=2014', time='201710020800')
            self.eq(t1[1].get('inet:web:chprofile:pv'), 'inet:web:acct:seen:min=2014/01/01 00:00:00.000')
            self.eq(t1[1].get('inet:web:chprofile:pv:prop'), 'inet:web:acct:seen:min')
            self.eq(t1[1].get('inet:web:chprofile:pv:intval'), 1388534400000)
            self.none(t1[1].get('inet:web:chprofile:pv:strval'))

            # We require the account to be present
            self.raises(PropNotFound, core.formTufoByProp, 'inet:web:chprofile', '*')

    def test_model_inet_postref_postmissingprops(self):
        with self.getRamCore() as core:

            postref_tufo = core.formTufoByProp('inet:web:postref', (('vertex.link/user', 'mypost 0.0.0.0'), ('inet:ipv4', 0)))
            self.nn(core.getTufoByProp('inet:web:post', ('vertex.link/user', 'mypost 0.0.0.0')))

            self.eq(postref_tufo[1]['tufo:form'], 'inet:web:postref')
            self.eq(postref_tufo[1]['inet:web:postref'], '804ec63392f4ea031bb3fd004dee209d')
            self.eq(postref_tufo[1]['inet:web:postref:post'], '68bc4607f0518963165536921d6e86fa')
            self.eq(postref_tufo[1]['inet:web:postref:xref'], 'inet:ipv4=0.0.0.0')
            self.eq(postref_tufo[1]['inet:web:postref:xref:prop'], 'inet:ipv4')
            self.eq(postref_tufo[1]['inet:web:postref:xref:intval'], 0)

            post_tufo = core.formTufoByProp('inet:web:post', ('vertex.link/user', 'mypost 0.0.0.0'))
            # Ensure we got the deconflicted node that was already made, not a new node
            self.notin('.new', post_tufo[1])
            self.eq(post_tufo[1]['inet:web:post'], postref_tufo[1]['inet:web:postref:post'])
            # Ensure that subs on the autoadd node are formed properly
            self.eq(post_tufo[1].get('inet:web:post:acct'), 'vertex.link/user')
            self.eq(post_tufo[1].get('inet:web:post:text'), 'mypost 0.0.0.0')
            # Ensure multiple subs were made into nodes
            self.nn(core.getTufoByProp('inet:web:acct', 'vertex.link/user'))
            self.nn(core.getTufoByProp('inet:user', 'user'))
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core.getTufoByProp('inet:fqdn', 'link'))

    def test_model_inet_addr(self):
        with self.getRamCore() as core:

            # ipv4
            valu, subs = core.getTypeNorm('inet:addr', '1.2.3.4')
            self.eq(valu, 'tcp://1.2.3.4')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.none(subs.get('port'))
            self.none(subs.get('host'))

            # ipv4:port
            valu, subs = core.getTypeNorm('inet:addr', '1.2.3.4:80')
            self.eq(valu, 'tcp://1.2.3.4:80')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['port'], 80)
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.none(subs.get('host'))

            # DWIM IPv6...
            valu, subs = core.getTypeNorm('inet:addr', '1.2.3.4:80')
            self.eq(valu, 'tcp://1.2.3.4:80')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['port'], 80)
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.none(subs.get('host'))

            # ipv6 port
            valu, subs = core.getTypeNorm('inet:addr', '[FF::56]:99')
            self.eq(valu, 'tcp://[ff::56]:99')
            self.eq(subs['port'], 99)
            self.eq(subs['ipv6'], 'ff::56')
            self.eq(subs['proto'], 'tcp')
            self.none(subs.get('ipv4'))
            self.none(subs.get('host'))

            # unadorned syntax...
            valu, subs = core.getTypeNorm('inet:addr', 'FF::56')
            self.eq(valu, 'tcp://[ff::56]')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv6'], 'ff::56')
            self.none(subs.get('ipv4'))
            self.none(subs.get('port'))
            self.none(subs.get('host'))

            valu, subs = core.getTypeNorm('inet:addr', '[::ffff:1.2.3.4]:8080')
            self.eq(valu, 'tcp://1.2.3.4:8080')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.eq(subs['ipv4'], 16909060,)
            self.eq(subs['port'], 8080)
            self.none(subs.get('host'))
            # Renorm the primary property (which no longer uses the ipv6 syntax
            nvalu, nsubs = core.getTypeNorm('inet:addr', valu)
            self.eq(nvalu, valu)
            self.eq(nsubs, subs)

            valu, subs = core.getTypeNorm('inet:addr', '::ffff:1.2.3.4')
            self.eq(valu, 'tcp://1.2.3.4')
            self.eq(subs['proto'], 'tcp')
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')
            self.eq(subs['ipv4'], 16909060,)
            self.none(subs.get('port'))
            self.none(subs.get('host'))

            host = s_common.guid('thx')
            valu, subs = core.getTypeNorm('inet:addr', 'HosT://%s:1138/' % host)
            self.eq(valu, 'host://%s:1138' % host)
            self.eq(subs['proto'], 'host')
            self.eq(subs['host'], host)
            self.eq(subs['port'], 1138)
            self.none(subs.get('ipv4'))
            self.none(subs.get('ipv6'))

            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'icmp://[FF::56]:99')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'icmp://8.6.7.5:309')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'tcp://8.6.7.256:309')
            self.raises(BadTypeValu, core.getTypeNorm, 'inet:addr', 'giggles://float.down.here/')

            host = s_common.guid()
            node = core.formTufoByProp('inet:client', 'host://%s' % (host,))
            self.eq(node[1]['inet:client:host'], host)
            self.eq(node[1]['inet:client:proto'], 'host')
            self.nn(core.getTufoByProp('it:host', host))

    def test_model_inet_server(self):

        with self.getRamCore() as core:

            valu, subs = core.getTypeNorm('inet:server', 'udp://1.2.3.4:80')
            self.eq(valu, 'udp://1.2.3.4:80')
            self.eq(subs['port'], 80)
            self.eq(subs['proto'], 'udp')
            self.eq(subs['ipv4'], 0x01020304)
            self.eq(subs['ipv6'], '::ffff:1.2.3.4')

    def test_model_inet_servfile(self):

        with self.getRamCore() as core:

            iden = s_common.guid()
            props = {'seen:min': 10, 'seen:max': 20}
            node = core.formTufoByProp('inet:servfile', ('tcp://1.2.3.4:443', iden), **props)
            self.eq(node[1]['inet:servfile:file'], iden)
            self.eq(node[1]['inet:servfile:server'], 'tcp://1.2.3.4:443')
            self.eq(node[1]['inet:servfile:server:port'], 443)
            self.eq(node[1]['inet:servfile:server:proto'], 'tcp')
            self.eq(node[1]['inet:servfile:server:ipv4'], 0x01020304)
            self.eq(node[1]['inet:servfile:server:ipv6'], '::ffff:1.2.3.4')
            self.eq(node[1]['inet:servfile:seen:min'], 10)
            self.eq(node[1]['inet:servfile:seen:max'], 20)

    def test_model_inet_download(self):

        with self.getRamCore() as core:

            iden = s_common.guid()
            props = {'time': 10, 'file': iden, 'server': 'tcp://1.2.3.4:80', 'client': 'tcp://5.6.7.8'}
            node = core.formTufoByProp('inet:download', '*', **props)
            self.eq(node[1].get('inet:download:time'), 10)
            self.eq(node[1].get('inet:download:file'), iden)
            self.eq(node[1].get('inet:download:server:proto'), 'tcp')
            self.eq(node[1].get('inet:download:server:port'), 80)
            self.eq(node[1].get('inet:download:server:ipv4'), 0x01020304)
            self.eq(node[1].get('inet:download:client:proto'), 'tcp')
            self.eq(node[1].get('inet:download:client:ipv4'), 0x05060708)

    def test_model_inet_wifi(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:wifi:ssid', 'hehe haha')
            self.eq(node[1].get('inet:wifi:ssid'), 'hehe haha')

            node = core.formTufoByProp('inet:wifi:ap', ('lololol', '01:02:03:04:05:06'))
            self.eq(node[1].get('inet:wifi:ap:ssid'), 'lololol')
            self.eq(node[1].get('inet:wifi:ap:bssid'), '01:02:03:04:05:06')

    def test_model_inet_iface(self):

        with self.getRamCore() as core:

            info = {
                'host': '*',
                'ipv6': 'ff::00',
                'ipv4': '1.2.3.4',
                'phone': 12345678910,
                'mac': 'ff:00:ff:00:ff:00',
                'wifi:ssid': 'hehe haha',
                'wifi:bssid': '00:ff:00:ff:00:ff',
                'mob:imei': 12345678901234,
                'mob:imsi': 12345678901234,
            }

            node = core.formTufoByProp('inet:iface', info)

            self.nn(core.getTufoByProp('it:host', node[1].get('inet:iface:host')))
            self.nn(core.getTufoByProp('inet:mac', node[1].get('inet:iface:mac')))
            self.nn(core.getTufoByProp('inet:ipv4', node[1].get('inet:iface:ipv4')))
            self.nn(core.getTufoByProp('inet:ipv6', node[1].get('inet:iface:ipv6')))
            self.nn(core.getTufoByProp('tel:phone', node[1].get('inet:iface:phone')))
            self.nn(core.getTufoByProp('inet:mac', node[1].get('inet:iface:wifi:bssid')))
            self.nn(core.getTufoByProp('inet:wifi:ssid', node[1].get('inet:iface:wifi:ssid')))
            self.nn(core.getTufoByProp('tel:mob:imei', node[1].get('inet:iface:mob:imei')))
            self.nn(core.getTufoByProp('tel:mob:imsi', node[1].get('inet:iface:mob:imsi')))

    def test_model_inet_urlredir(self):

        with self.getRamCore() as core:

            tick = s_time.parse('20161217')
            tock = s_time.parse('20170216')

            props = {'seen:min': tick, 'seen:max': tock}
            node = core.formTufoByProp('inet:urlredir', ('http://foo.com/', 'http://bar.com/'), **props)

            self.nn(core.getTufoByProp('inet:url', 'http://foo.com/'))
            self.nn(core.getTufoByProp('inet:url', 'http://bar.com/'))

            self.eq(node[1].get('inet:urlredir:src'), 'http://foo.com/')
            self.eq(node[1].get('inet:urlredir:src:fqdn'), 'foo.com')

            self.eq(node[1].get('inet:urlredir:dst'), 'http://bar.com/')
            self.eq(node[1].get('inet:urlredir:dst:fqdn'), 'bar.com')

            self.eq(node[1].get('inet:urlredir:seen:min'), tick)
            self.eq(node[1].get('inet:urlredir:seen:max'), tock)

    def test_model_inet_rfc2822_addr(self):

        with self.getRamCore() as core:

            self.raises(BadTypeValu, core.formTufoByProp, 'inet:rfc2822:addr', 20)

            n0 = core.formTufoByProp('inet:rfc2822:addr', 'FooBar')
            n1 = core.formTufoByProp('inet:rfc2822:addr', 'visi@vertex.link')
            n2 = core.formTufoByProp('inet:rfc2822:addr', 'foo bar<visi@vertex.link>')
            n3 = core.formTufoByProp('inet:rfc2822:addr', 'foo bar <visi@vertex.link>')
            n4 = core.formTufoByProp('inet:rfc2822:addr', '"foo bar "   <visi@vertex.link>')
            n5 = core.formTufoByProp('inet:rfc2822:addr', '<visi@vertex.link>')

            self.eq(n0[1].get('inet:rfc2822:addr'), 'foobar')
            self.none(n0[1].get('inet:rfc2822:addr:name'))
            self.none(n0[1].get('inet:rfc2822:addr:addr'))

            self.eq(n1[1].get('inet:rfc2822:addr'), 'visi@vertex.link')
            self.eq(n1[1].get('inet:rfc2822:addr:email'), 'visi@vertex.link')
            self.none(n1[1].get('inet:rfc2822:addr:name'))

            self.eq(n2[1].get('inet:rfc2822:addr'), 'foo bar <visi@vertex.link>')
            self.eq(n2[1].get('inet:rfc2822:addr:name'), 'foo bar')
            self.eq(n2[1].get('inet:rfc2822:addr:email'), 'visi@vertex.link')

            self.eq(n2[0], n3[0])
            self.eq(n2[0], n4[0])
            self.eq(n1[0], n5[0])

    def test_model_inet_http(self):

        with self.getRamCore() as core:

            tick = 0x01010101
            flow = s_common.guid()
            host = s_common.guid()
            body = s_common.guid()

            props = {
                'flow': flow,
                'time': tick,
                'host': host,
                'method': 'HeHe',
                'path': '/foo/bar',
                'query': 'baz=faz&woot=haha',
                'body': body,
            }

            requ = core.formTufoByProp('inet:http:request', '*', **props)

            iden = requ[1].get('inet:http:request')

            self.eq(requ[1]['inet:http:request:flow'], flow)
            self.eq(requ[1]['inet:http:request:time'], tick)
            self.eq(requ[1]['inet:http:request:host'], host)
            self.eq(requ[1]['inet:http:request:method'], 'HeHe')
            self.eq(requ[1]['inet:http:request:path'], '/foo/bar')
            self.eq(requ[1]['inet:http:request:query'], 'baz=faz&woot=haha')

            node = core.formTufoByProp('inet:http:reqhead', (iden, ('User-Agent', 'BillyBob')))

            self.eq(node[1].get('inet:http:reqhead:request'), iden)
            self.eq(node[1].get('inet:http:reqhead:header:name'), 'user-agent')
            self.eq(node[1].get('inet:http:reqhead:header:value'), 'BillyBob')

            node = core.getTufoByProp('inet:http:header', ('User-Agent', 'BillyBob'))
            self.eq(node[1].get('inet:http:header:name'), 'user-agent')
            self.eq(node[1].get('inet:http:header:value'), 'BillyBob')

            node = core.formTufoByProp('inet:http:reqhead', (iden, ('Host', 'vertex.ninja')))
            self.eq(node[1].get('inet:http:reqhead:request'), iden)
            self.eq(node[1].get('inet:http:reqhead:header:name'), 'host')
            self.eq(node[1].get('inet:http:reqhead:header:value'), 'vertex.ninja')

            node = core.getTufoByProp('inet:http:header', ('Host', 'vertex.ninja'))
            self.eq(node[1].get('inet:http:header:name'), 'host')
            self.eq(node[1].get('inet:http:header:value'), 'vertex.ninja')

            node = core.formTufoByProp('inet:http:reqparam', (iden, ('baz', 'faz')))
            self.eq(node[1].get('inet:http:reqparam:request'), iden)
            self.eq(node[1].get('inet:http:reqparam:param:name'), 'baz')
            self.eq(node[1].get('inet:http:reqparam:param:value'), 'faz')

            props = {
                'time': tick,
                'host': host,
                'request': iden,
                'code': 31337,
                'reason': 'too leet',
                'flow': flow,
                'body': body,
            }

            resp = core.formTufoByProp('inet:http:response', '*', **props)
            self.eq(resp[1]['inet:http:response:request'], iden)
            self.eq(resp[1]['inet:http:response:flow'], flow)
            self.eq(resp[1]['inet:http:response:time'], tick)
            self.eq(resp[1]['inet:http:response:host'], host)
            self.eq(resp[1]['inet:http:response:code'], 31337)
            self.eq(resp[1]['inet:http:response:reason'], 'too leet')
            self.eq(resp[1]['inet:http:response:body'], body)

            ridn = resp[1].get('inet:http:response')

# -*- coding: UTF-8 -*-
from __future__ import absolute_import,unicode_literals
import base64

import synapse.cortex as s_cortex
import synapse.lib.types as s_types

from synapse.tests.common import *

class DataTypesTest(SynTest):

    def test_datatype_basics(self):

        tlib = s_types.TypeLib()
        self.true( tlib.isDataType('inet:url') )
        self.true( isinstance(tlib.getDataType('inet:url'), s_types.DataType) )

        self.none( tlib.getDataType('newp') )
        self.raises( NoSuchType, tlib.reqDataType, 'newp' )

    def test_datatype_inet_url(self):
        tlib = s_types.TypeLib()

        self.assertRaises( BadTypeValu, tlib.getTypeNorm, 'inet:url', 'newp' )
        self.eq( tlib.getTypeNorm('inet:url','http://WoOt.com/HeHe')[0], 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeNorm('inet:url','HTTP://WoOt.com/HeHe')[0], 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeNorm('inet:url','HttP://Visi:Secret@WoOt.com/HeHe&foo=10')[0], 'http://Visi:Secret@woot.com/HeHe&foo=10' )

        self.eq( tlib.getTypeFrob('inet:url','http://WoOt.com/HeHe')[0], 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeFrob('inet:url','HTTP://WoOt.com/HeHe')[0], 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeFrob('inet:url','HttP://Visi:Secret@WoOt.com/HeHe&foo=10')[0], 'http://Visi:Secret@woot.com/HeHe&foo=10' )

        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'inet:url', 'newp' )
        self.eq( tlib.getTypeParse('inet:url','http://WoOt.com/HeHe')[0], 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeParse('inet:url','HTTP://WoOt.com/HeHe')[0], 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeParse('inet:url','HttP://Visi:Secret@WoOt.com/HeHe&foo=10')[0], 'http://Visi:Secret@woot.com/HeHe&foo=10' )

        self.eq( tlib.getTypeRepr('inet:url','http://woot.com/HeHe'), 'http://woot.com/HeHe' )

    def test_datatype_inet_ipv4(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:ipv4',0x01020304)[0], 0x01020304 )
        self.eq( tlib.getTypeFrob('inet:ipv4','0x01020304')[0], 0x01020304 )
 
        self.eq( tlib.getTypeFrob('inet:ipv4','1.2.3.4')[0], 0x01020304 )
        self.eq( tlib.getTypeFrob('inet:ipv4',0x01020304)[0], 0x01020304 )

        self.eq( tlib.getTypeParse('inet:ipv4','1.2.3.4')[0], 0x01020304 )

        self.eq( tlib.getTypeRepr('inet:ipv4',0x01020304), '1.2.3.4' )

    def test_datatype_inet_tcp4(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:tcp4',0x010203040002)[0], 0x010203040002 )

        self.eq( tlib.getTypeFrob('inet:tcp4',0x010203040002)[0], 0x010203040002 )
        self.eq( tlib.getTypeFrob('inet:tcp4','1.2.3.4:2')[0], 0x010203040002 )

        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'inet:tcp4', 'newp' )
        self.eq( tlib.getTypeParse('inet:tcp4','1.2.3.4:2')[0], 0x010203040002 )

        self.eq( tlib.getTypeRepr('inet:tcp4',0x010203040002), '1.2.3.4:2' )

    def test_datatype_inet_udp4(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:udp4',0x010203040002)[0], 0x010203040002 )

        self.eq( tlib.getTypeFrob('inet:udp4',0x010203040002)[0], 0x010203040002 )
        self.eq( tlib.getTypeFrob('inet:udp4','1.2.3.4:2')[0], 0x010203040002 )

        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'inet:udp4', 'newp' )
        self.eq( tlib.getTypeParse('inet:udp4','1.2.3.4:2')[0], 0x010203040002 )

        self.eq( tlib.getTypeRepr('inet:udp4',0x010203040002), '1.2.3.4:2' )

    def test_datatype_inet_port(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:port', '70000' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:port', 0xffffffff )

        self.eq( tlib.getTypeNorm('inet:port', 20)[0], 20 )

    def test_datatype_inet_mac(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:mac', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:mac', 'newp' )

        self.eq( tlib.getTypeFrob('inet:mac', 'FF:FF:FF:FF:FF:FF')[0], 'ff:ff:ff:ff:ff:ff' )
        self.eq( tlib.getTypeNorm('inet:mac', 'FF:FF:FF:FF:FF:FF')[0], 'ff:ff:ff:ff:ff:ff' )
        self.eq( tlib.getTypeParse('inet:mac', 'FF:FF:FF:FF:FF:FF')[0], 'ff:ff:ff:ff:ff:ff' )
        self.eq( tlib.getTypeRepr('inet:mac', 'ff:ff:ff:ff:ff:ff'), 'ff:ff:ff:ff:ff:ff' )

    def test_datatype_inet_email(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:email', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:email', 'newp' )

        self.eq( tlib.getTypeParse('inet:email', 'ViSi@Woot.Com')[0], 'visi@woot.com' )

        self.eq( tlib.getTypeNorm('inet:email', 'ViSi@Woot.Com')[0], 'visi@woot.com' )

        self.eq( tlib.getTypeRepr('inet:email', 'visi@woot.com'), 'visi@woot.com' )

    def test_datatype_guid(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'guid', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'guid', 'newp' )

        self.eq( tlib.getTypeParse('guid', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeParse('guid', '00010203-0405-0607-0809-0A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeFrob('guid', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeNorm('guid', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeRepr('guid', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_guid_sub(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot',subof='guid')

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'woot', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'woot', 'newp' )

        self.eq( tlib.getTypeParse('woot', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeNorm('woot', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeFrob('woot', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeRepr('guid', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_hash_md5(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'hash:md5', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'hash:md5', 'newp' )

        self.eq( tlib.getTypeParse('hash:md5', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeNorm('hash:md5', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeFrob('hash:md5', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeRepr('hash:md5', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_inet_ipv6(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:ipv6', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', '[fffffffffffffffffffffffff::2]:80' )

        self.eq( tlib.getTypeParse('inet:ipv6', 'AF:00::02')[0], 'af::2')
        self.eq( tlib.getTypeNorm('inet:ipv6', 'AF:00::02')[0], 'af::2')
        self.eq( tlib.getTypeRepr('inet:ipv6', 'af::2'), 'af::2')

        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8::1:1:1:1:1')[0], '2001:db8:0:1:1:1:1:1')
        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8:0:1:1:1:1:1')[0], '2001:db8:0:1:1:1:1:1')

        self.eq( tlib.getTypeFrob('inet:ipv6', '2001:db8::1:1:1:1:1')[0], '2001:db8:0:1:1:1:1:1')

        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8::0:1')[0], '2001:db8::1')
        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8:0:0:0:0:2:1')[0], '2001:db8::2:1')

        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8::')[0], '2001:db8::')

        self.eq( tlib.getTypeRepr('inet:srv6', '[af::2]:80'), '[af::2]:80')
        self.eq( tlib.getTypeParse('inet:srv6', '[AF:00::02]:80')[0], '[af::2]:80')
        self.eq( tlib.getTypeNorm('inet:srv6', '[AF:00::02]:80')[0], '[af::2]:80')
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', '[AF:00::02]:999999')
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', '[AF:00::02]:-1')

    def test_datatype_inet_cidr(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:cidr4', '1.2.3.0/33' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:cidr4', '1.2.3.0/-1' )

        self.eq( tlib.getTypeNorm('inet:cidr4', '1.2.3.0/24'), ('1.2.3.0/24', {'ipv4':16909056, 'mask':24}) )
        self.eq( tlib.getTypeRepr('inet:cidr4', '1.2.3.0/24'), '1.2.3.0/24')

    def test_datatype_str(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'str', 10 )

        self.eq( tlib.getTypeNorm('str','foo')[0], 'foo' )
        self.eq( tlib.getTypeFrob('str','foo')[0], 'foo' )
        self.eq( tlib.getTypeParse('str','bar')[0], 'bar' )

    def test_datatype_str_enums(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot',subof='str',enums='hehe,haha,hoho', lower=1)

        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'woot', 'asdf' )
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'woot', 'asdf' )

        self.eq( tlib.getTypeNorm('woot','HeHe')[0], 'hehe' )
        self.eq( tlib.getTypeFrob('woot','HeHe')[0], 'hehe' )
        self.eq( tlib.getTypeParse('woot','HeHe')[0], 'hehe' )

    def test_datatype_str_hex(self):
        tlib = s_types.TypeLib()

        #self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'str:hex', 0xFFF)
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'str:hex', '0xFFF')
        self.eq(tlib.getTypeNorm('str:hex', 'FfF')[0], 'fff')
        self.eq(tlib.getTypeNorm('str:hex', '12345')[0], '12345')
        self.eq(tlib.getTypeNorm('str:hex', '12A45')[0], '12a45')

        self.none(tlib.getTypeFrob('str:hex', '0xFFF')[0])
        self.eq(tlib.getTypeFrob('str:hex', 0xFfF)[0], 'fff')
        self.eq(tlib.getTypeFrob('str:hex', 'FFF')[0], 'fff')
        self.eq(tlib.getTypeFrob('str:hex', '1A2b3C')[0], '1a2b3c')
        self.eq(tlib.getTypeFrob('str:hex', 0x1A2b3C)[0], '1a2b3c')
        self.eq(tlib.getTypeFrob('str:hex', '12345')[0], '12345') # already str
        self.eq(tlib.getTypeFrob('str:hex', 12345)[0], '3039')

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'str:hex', '0xFFF')
        #self.assertRaises(BadTypeValu, tlib.getTypeParse, 'str:hex', 0xFFF)
        #self.assertRaises(BadTypeValu, tlib.getTypeParse, 'str:hex', 123)
        self.eq(tlib.getTypeParse('str:hex', '10001')[0], '10001')
        self.eq(tlib.getTypeParse('str:hex', 'FFF')[0], 'fff')

        tlib.addType('woot', subof='sepr', sep='/', fields='a,str:hex|b,str:hex')
        self.eq(tlib.getTypeFrob('woot', 'AAA/BBB')[0], 'aaa/bbb')
        self.eq(tlib.getTypeFrob('woot', '123456/BBB')[0], '123456/bbb') # already str
        self.eq(tlib.getTypeFrob('woot', (123456, 'BBB'))[0], '1e240/bbb')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'woot', '123x/aaaa')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'woot', '0x123/aaaa')

    def test_datatype_dup(self):
        tlib = s_types.TypeLib()

        self.assertRaises(DupTypeName, tlib.addType, 'inet:port', subof='int' )

    def test_datatype_bool(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'bool', 'bogus' )

        self.assertTrue( tlib.getTypeParse('bool','1')[0] )
        self.assertTrue( tlib.getTypeParse('bool','t')[0] )
        self.assertTrue( tlib.getTypeParse('bool','y')[0] )
        self.assertTrue( tlib.getTypeParse('bool','TrUe')[0] )
        self.assertTrue( tlib.getTypeParse('bool','yEs')[0] )
        self.assertTrue( tlib.getTypeParse('bool','ON')[0] )

        self.assertFalse( tlib.getTypeParse('bool','0')[0] )
        self.assertFalse( tlib.getTypeParse('bool','f')[0] )
        self.assertFalse( tlib.getTypeParse('bool','n')[0] )
        self.assertFalse( tlib.getTypeParse('bool','FaLsE')[0] )
        self.assertFalse( tlib.getTypeParse('bool','nO')[0] )
        self.assertFalse( tlib.getTypeParse('bool','OFF')[0] )

        self.assertEqual( tlib.getTypeRepr('bool',1), 'True' )
        self.assertEqual( tlib.getTypeRepr('bool',0), 'False' )

        self.assertEqual( tlib.getTypeNorm('bool',9)[0], 1)
        self.assertEqual( tlib.getTypeNorm('bool',0)[0], 0)

        self.assertEqual( tlib.getTypeFrob('bool',9)[0], 1)
        self.assertFalse( tlib.getTypeFrob('bool','f')[0] )
        self.assertFalse( tlib.getTypeFrob('bool','n')[0] )
        self.assertFalse( tlib.getTypeFrob('bool','FaLsE')[0] )

    def test_type_comp(self):
        tlib = s_types.TypeLib()
        tlib.addType('foo:bar',subof='comp',types='inet:fqdn,inet:ipv4', names='hehe,haha')

        valu,subs = tlib.getTypeNorm('foo:bar', ('WOOT.COM',0x01020304) )
        self.eq( valu, '47e2e1c0f894266153f836a75440f803' )
        self.eq( subs.get('hehe'), 'woot.com' )
        self.eq( subs.get('haha'), 0x01020304 )

    #def test_type_comp_err(self):
        #tlib = s_types.TypeLib()
        #self.assertRaises( BadInfoValu, tlib.addType, 'fake:newp', subof='comp',fields='asdfqwer')

    def test_datatype_int_minmax(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot:min',subof='int',ismin=1)
        tlib.addType('woot:max',subof='int',ismax=1)

        self.eq( tlib.getTypeNorm('woot:min', 20, oldval=40)[0], 20 )
        self.eq( tlib.getTypeNorm('woot:min', 40, oldval=20)[0], 20 )

        self.eq( tlib.getTypeNorm('woot:max', 20, oldval=40)[0], 40 )
        self.eq( tlib.getTypeNorm('woot:max', 40, oldval=20)[0], 40 )

    def test_datatype_int_repr(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeRepr('int', -1), '-1')
        self.eq( tlib.getTypeRepr('int', 1), '1')

        tlib.addType('woot:min',subof='int',ismin=1)
        self.eq( tlib.getTypeRepr('woot:min', 1), '1')

    def test_datatype_fqdn(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:fqdn','WOOT.COM')[0], 'woot.com')
        self.eq( tlib.getTypeNorm('inet:fqdn','WO-OT.COM')[0], 'wo-ot.com')
        self.eq( tlib.getTypeFrob('inet:fqdn','WOOT.COM')[0], 'woot.com')
        self.eq( tlib.getTypeFrob('inet:fqdn','WO-OT.COM')[0], 'wo-ot.com')
        self.eq( tlib.getTypeParse('inet:fqdn','WOOT.COM')[0], 'woot.com')
        self.eq( tlib.getTypeParse('inet:fqdn','WO-OT.COM')[0], 'wo-ot.com')

    #def test_type_stor_info(self):
        #tlib = s_types.TypeLib()
        #self.assertRaises( BadStorValu, tlib.addType, 'fake:newp', subof='comp',fields=() )

    def test_type_pend(self):
        tlib = s_types.TypeLib()
        self.assertFalse( tlib.addType('foo',subof='bar') )
        self.assertTrue( tlib.addType('bar',subof='int') )
        self.assertIsNotNone( tlib.getDataType('foo') )

    def test_type_sepr(self):
        tlib = s_types.TypeLib()
        tlib.addType('siteuser', subof='sepr', sep='/', fields='foo,inet:fqdn|bar,inet:user')
        self.eq( tlib.getTypeNorm('siteuser','WOOT.COM/visi')[0], 'woot.com/visi' )
        self.eq( tlib.getTypeParse('siteuser','WOOT.COM/visi')[0], 'woot.com/visi' )

        norm,subs = tlib.getTypeNorm('siteuser','WOOT.COM/Visi')
        self.eq(subs.get('foo'),'woot.com')
        self.eq(subs.get('bar'),'Visi')

    def test_type_sepr_reverse(self):
        tlib = s_types.TypeLib()

        tlib.addType('foo',subof='sepr',sep='/',fields='first,str:lwr|rest,str:lwr',reverse=1)
        foo = tlib.getTypeNorm('foo','/home/user/Downloads')
        self.eq( foo[1].get('first'), '/home/user' )
        self.eq( foo[1].get('rest'), 'downloads' )

    def test_type_sepr_frob(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot',subof='sepr',sep='/',fields='a,str:hex|b,str:hex')
        tlib.addType('wootaddr',subof='sepr',sep='/',fields='a,str:hex|b,str:hex|c,inet:ipv4')
        tlib.addType('underwoot',subof='sepr',sep='_',fields='c,woot|d,woot')
        tlib.addType('badwoot',subof='sepr',sep='/',fields='c,woot|d,woot')

        self.eq(tlib.getTypeFrob('woot', '12345/67890')[0], '12345/67890') # already str
        self.eq(tlib.getTypeFrob('woot', (12345, 67890))[0], '3039/10932')
        self.eq(tlib.getTypeFrob('woot', [12345, 67890])[0], '3039/10932')

        self.eq(tlib.getTypeFrob('underwoot', '12/34_56/78')[0], '12/34_56/78') # already str
        self.eq(tlib.getTypeFrob('underwoot', ((12,34), (56,78)))[0], 'c/22_38/4e')
        self.eq(tlib.getTypeFrob('underwoot', [(12,34), [56,78]])[0], 'c/22_38/4e')

        self.none(tlib.getTypeFrob('badwoot', '1/2/3/4')[0])

        self.eq(tlib.getTypeFrob('wootaddr', [12345, 67890, 0])[0], '3039/10932/0.0.0.0')
        self.eq(tlib.getTypeFrob('wootaddr', [12345, 67890, '192.168.1.1'])[0], '3039/10932/192.168.1.1')

    def test_type_sepr_parse(self):
        tlib = s_types.TypeLib()
        tlib.addType('woot',subof='sepr',sep='/',fields='a,str:hex|b,str:hex')
        self.eq(tlib.getTypeParse('woot', '12345/67890')[0], '12345/67890')

    def test_type_str_nullval(self):
        tlib = s_types.TypeLib()
        tlib.addType('woot', subof='str', regex='^[0-9]+$', nullval='??')
        self.eq( tlib.getTypeNorm('woot','10')[0], '10' )
        self.eq( tlib.getTypeParse('woot','10')[0], '10' )

        self.eq( tlib.getTypeNorm('woot','??')[0], '??' )
        self.eq( tlib.getTypeParse('woot','??')[0], '??' )

        self.assertRaises( BadTypeValu, tlib.getTypeNorm, 'woot', 'qwer' )
        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'woot', 'qwer' )

    def test_type_bases(self):
        with s_cortex.openurl('ram:///') as core:
            self.eq( tuple(core.getTypeBases('inet:dns:look')), ('str','guid','inet:dns:look') )

    def test_type_issub(self):
        with s_cortex.openurl('ram:///') as core:
            self.assertTrue( core.isSubType('inet:dns:look', 'guid') )
            self.assertFalse( core.isSubType('inet:dns:look', 'int') )
            self.assertTrue( core.isSubType('str', 'str') )

    def test_type_getTypeInfo(self):
        with s_cortex.openurl('ram:///') as core:
            core.addType('foo:bar',subof='inet:ipv4')
            self.assertIsNotNone( core.getTypeInfo('foo:bar','ex') )

    #def test_type_comp_recursive(self):
        #tlib = s_types.TypeLib()

        #tlib.addType('path',subof='sepr',sep='/',fields='dirname,path|filename,str:lwr',reverse=1)
        #foo = tlib.getTypeNorm('path','/home/user/Downloads')
        #self.eq( foo[1].get('dirname'), '/home/user' )
        #self.eq( foo[1].get('filename'), 'downloads' )

        #foo2 = tlib.getTypeNorm('path','/home')
        #self.eq( foo2[1].get('dirname'), '' )
        #self.eq( foo2[1].get('filename'), 'home' )

        #foo3 = tlib.getTypeNorm('path','/')
        #self.eq( foo3[1].get('dirname'), '' )
        #self.eq( foo3[1].get('filename'), '' )

        #self.assertRaises( BadTypeValu, tlib.getTypeNorm, 'path', 'some-filename' )

    def test_type_json(self):
        tlib = s_types.TypeLib()
        self.eq( tlib.getTypeNorm('json','{  "woot"       :10}')[0], '{"woot":10}' )
        self.eq( tlib.getTypeFrob('json',{'woot':10})[0], '{"woot":10}' )
        self.eq( tlib.getTypeParse('json','{"woot":10}')[0], '{"woot":10}' )

        # cant frob json string unless it's valid json... ( can't tell the difference )
        self.none(tlib.getTypeFrob('json', 'derp' )[0])
        #self.assertRaises( BadTypeValu, tlib.getTypeParse, 'json', {'woot':10} )

    def test_type_fqdn(self):
        tlib = s_types.TypeLib()
        prop = 'inet:fqdn'
        fqdns = ('test.example.com', 'test.èxamplè.com', 'tèst.èxamplè.com', 'xn--test.xampl.com-zjbf', 'xn--tst.xampl.com-wgbdf')
        idnas = ('test.example.com', 'test.èxamplè.com', 'tèst.èxamplè.com',        'test.èxamplè.com',        'tèst.èxamplè.com')
        domns = (     'example.com',      'èxamplè.com',      'èxamplè.com',             'èxamplè.com',             'èxamplè.com')
        hosts = (            'test',             'test',             'tèst',                    'test',                    'tèst')

        for i in range(len(fqdns)):
            self.eq(tlib.getTypeNorm(prop, fqdns[i])[0], idnas[i])
            self.eq(tlib.getTypeFrob(prop, fqdns[i])[0], idnas[i])
            self.eq(tlib.getTypeRepr(prop, fqdns[i]), fqdns[i])

        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:fqdn', '!@#$%')

    def test_type_phone(self):
        tlib = s_types.TypeLib()
        prop = 'tel:phone'

        self.eq(tlib.getTypeNorm(prop, 1234567890)[0], 1234567890)
        self.eq(tlib.getTypeParse(prop, '123 456 7890')[0], 1234567890)

        self.eq(tlib.getTypeRepr(prop, 12345678901), '+1 (234) 567-8901')
        self.eq(tlib.getTypeRepr(prop, 9999999999), '+9999999999')

    def test_type_time_timeepoch(self):
        tlib = s_types.TypeLib()
        SECOND_MS = 1000
        MINUTE_SEC = 60
        MINUTE_MS = MINUTE_SEC * 1000
        HOUR_SEC = MINUTE_SEC * 60
        HOUR_MS = HOUR_SEC * 1000
        DAY_SEC = HOUR_SEC * 24
        DAY_MS = DAY_SEC * 1000
        EPOCH_FEB_SEC = 2678400
        EPOCH_FEB_MS = 2678400000

        self.eq(tlib.getTypeParse('time',      '1970')[0],             0)
        self.eq(tlib.getTypeParse('time:epoch','1970')[0],             0)
        self.eq(tlib.getTypeParse('time',      '1970 02')[0],          EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 02')[0],          EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0201')[0],        EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0201')[0],        EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0202')[0],        EPOCH_FEB_MS + DAY_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0202')[0],        EPOCH_FEB_SEC + DAY_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0201 00')[0],     EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0201 00')[0],     EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0201 01')[0],     EPOCH_FEB_MS + HOUR_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0201 01')[0],     EPOCH_FEB_SEC + HOUR_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0201 0000')[0],   EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0201 0000')[0],   EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0201 0001')[0],   EPOCH_FEB_MS + MINUTE_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0201 0001')[0],   EPOCH_FEB_SEC + MINUTE_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0201 000000')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0201 000000')[0], EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time',      '1970 0201 000001')[0], EPOCH_FEB_MS + SECOND_MS)
        self.eq(tlib.getTypeParse('time:epoch','1970 0201 000001')[0], EPOCH_FEB_SEC + 1)

        #self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time', 0)
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time','19700')
        self.eq(tlib.getTypeParse('time','1970 0201 000000 0')[0],   EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time','1970 0201 000000 1')[0],   EPOCH_FEB_MS + 100)
        self.eq(tlib.getTypeParse('time','1970 0201 000000 00')[0],  EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time','1970 0201 000000 12')[0],  EPOCH_FEB_MS + 120)
        self.eq(tlib.getTypeParse('time','1970 0201 000000 000')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time','1970 0201 000000 123')[0], EPOCH_FEB_MS + 123)
        self.eq(tlib.getTypeParse('time','1970-01-01 00:00:00.010')[0], 10)
        self.eq(tlib.getTypeParse('time','1q9w7e0r0t1y0u1i0o0p0a0s0d0f0g0h0j')[0], 0)

        #self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch', 0)
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','19700')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1970 0201 000000 0')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1970 0201 000000 1')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1970 0201 000000 00')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1970 0201 000000 12')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1970 0201 000000 000')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1970 0201 000000 123')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1970-01-01 00:00:00.010')
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'time:epoch','1q9w7e0r0t1y0u1i0o0p0a0s0d0f0g0h1j')

        self.eq(tlib.getTypeParse('time','1970')[0], tlib.getTypeParse('time:epoch','1970')[0]*1000) # time should = epoch*1000
        self.eq(tlib.getTypeParse('time','19700101 123456')[0], tlib.getTypeParse('time:epoch','19700101 123456')[0]*1000) # time should = epoch*1000

        self.eq(tlib.getTypeRepr('time',       -1), '1969/12/31 23:59:59.999')
        self.eq(tlib.getTypeRepr('time:epoch', -1), '1969/12/31 23:59:59')
        self.eq(tlib.getTypeRepr('time',        0), '1970/01/01 00:00:00.000')
        self.eq(tlib.getTypeRepr('time:epoch',  0), '1970/01/01 00:00:00')
        self.eq(tlib.getTypeRepr('time',        1), '1970/01/01 00:00:00.001')
        self.eq(tlib.getTypeRepr('time:epoch',  1), '1970/01/01 00:00:01')

        self.eq(tlib.getTypeNorm('time',       -1)[0], -1)
        self.eq(tlib.getTypeNorm('time:epoch', -1)[0], -1)
        self.eq(tlib.getTypeNorm('time',        0)[0],  0)
        self.eq(tlib.getTypeNorm('time:epoch',  0)[0],  0)
        self.eq(tlib.getTypeNorm('time',        1)[0],  1)
        self.eq(tlib.getTypeNorm('time:epoch',  1)[0],  1)
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'time','0')
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'time:epoch','0')

        self.eq(tlib.getTypeFrob('time',       '1969/12/31 23:59:59.999')[0], -1)
        self.eq(tlib.getTypeFrob('time:epoch', '1969/12/31 23:59:59')[0],     -1)
        self.eq(tlib.getTypeFrob('time',       '1970/01/01 00:00:00.000')[0],  0)
        self.eq(tlib.getTypeFrob('time:epoch', '1970/01/01 00:00:00')[0],      0)
        self.eq(tlib.getTypeFrob('time',       '1970/01/01 00:00:00.001')[0],  1)
        self.eq(tlib.getTypeFrob('time:epoch', '1970/01/01 00:00:01')[0],      1)
        self.eq(tlib.getTypeFrob('time',                          -1)[0],     -1)
        self.eq(tlib.getTypeFrob('time:epoch',                    -1)[0],     -1)
        self.eq(tlib.getTypeFrob('time',                           0)[0],      0)
        self.eq(tlib.getTypeFrob('time:epoch',                     0)[0],      0)
        self.eq(tlib.getTypeFrob('time',                           1)[0],      1)
        self.eq(tlib.getTypeFrob('time:epoch',                     1)[0],      1)

    def test_type_cast(self):
        tlib = s_types.TypeLib()

        def cast(x):
            return x.upper()

        tlib.addTypeCast("toupper",cast)

        self.eq( tlib.getTypeCast('str:lwr','  HeHe  '), 'hehe' )
        self.eq( tlib.getTypeCast('toupper','HeHe'), 'HEHE' )
        self.eq( tlib.getTypeCast('make:guid','visi'), '98db59098e385f0bfdec8a6a0a6118b3')

    def test_str_strip(self):
        tlib = s_types.TypeLib()
        self.eq( tlib.getTypeCast('str:lwr',' ASDF  '), 'asdf' )

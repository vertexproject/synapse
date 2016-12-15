import base64

import synapse.lib.thishost as s_thishost
import synapse.lib.types as s_types

from synapse.tests.common import *

class DataTypesTest(SynTest):

    def test_datatype_basics(self):

        tlib = s_types.TypeLib()
        self.assertTrue( isinstance(tlib.getDataType('inet:url'), s_types.DataType) )

        self.assertIsNone( tlib.getDataType('newp') )
        self.assertRaises( NoSuchType, tlib.reqDataType, 'newp' )

    def test_datatype_inet_url(self):
        tlib = s_types.TypeLib()

        self.assertRaises( BadTypeValu, tlib.getTypeNorm, 'inet:url', 'newp' )
        self.eq( tlib.getTypeNorm('inet:url','http://WoOt.com/HeHe'), 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeNorm('inet:url','HTTP://WoOt.com/HeHe'), 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeNorm('inet:url','HttP://Visi:Secret@WoOt.com/HeHe&foo=10'), 'http://Visi:Secret@woot.com/HeHe&foo=10' )

        self.eq( tlib.getTypeFrob('inet:url','http://WoOt.com/HeHe'), 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeFrob('inet:url','HTTP://WoOt.com/HeHe'), 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeFrob('inet:url','HttP://Visi:Secret@WoOt.com/HeHe&foo=10'), 'http://Visi:Secret@woot.com/HeHe&foo=10' )

        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'inet:url', 'newp' )
        self.eq( tlib.getTypeParse('inet:url','http://WoOt.com/HeHe'), 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeParse('inet:url','HTTP://WoOt.com/HeHe'), 'http://woot.com/HeHe' )
        self.eq( tlib.getTypeParse('inet:url','HttP://Visi:Secret@WoOt.com/HeHe&foo=10'), 'http://Visi:Secret@woot.com/HeHe&foo=10' )

        self.eq( tlib.getTypeRepr('inet:url','http://woot.com/HeHe'), 'http://woot.com/HeHe' )

    def test_datatype_inet_ipv4(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:ipv4',0x01020304), 0x01020304 )

        self.eq( tlib.getTypeFrob('inet:ipv4','1.2.3.4'), 0x01020304 )
        self.eq( tlib.getTypeFrob('inet:ipv4',0x01020304), 0x01020304 )

        self.eq( tlib.getTypeParse('inet:ipv4','1.2.3.4'), 0x01020304 )

        self.eq( tlib.getTypeRepr('inet:ipv4',0x01020304), '1.2.3.4' )

    def test_datatype_inet_tcp4(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:tcp4',0x010203040002), 0x010203040002 )

        self.eq( tlib.getTypeFrob('inet:tcp4',0x010203040002), 0x010203040002 )
        self.eq( tlib.getTypeFrob('inet:tcp4','1.2.3.4:2'), 0x010203040002 )

        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'inet:tcp4', 'newp' )
        self.eq( tlib.getTypeParse('inet:tcp4','1.2.3.4:2'), 0x010203040002 )

        self.eq( tlib.getTypeRepr('inet:tcp4',0x010203040002), '1.2.3.4:2' )

    def test_datatype_inet_udp4(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:udp4',0x010203040002), 0x010203040002 )

        self.eq( tlib.getTypeFrob('inet:udp4',0x010203040002), 0x010203040002 )
        self.eq( tlib.getTypeFrob('inet:udp4','1.2.3.4:2'), 0x010203040002 )

        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'inet:udp4', 'newp' )
        self.eq( tlib.getTypeParse('inet:udp4','1.2.3.4:2'), 0x010203040002 )

        self.eq( tlib.getTypeRepr('inet:udp4',0x010203040002), '1.2.3.4:2' )

    def test_datatype_inet_port(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:port', '70000' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:port', 0xffffffff )

        self.eq( tlib.getTypeNorm('inet:port', 20), 20 )

    def test_datatype_inet_mac(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:mac', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:mac', 'newp' )

        self.eq( tlib.getTypeFrob('inet:mac', 'FF:FF:FF:FF:FF:FF'), 'ff:ff:ff:ff:ff:ff' )
        self.eq( tlib.getTypeNorm('inet:mac', 'FF:FF:FF:FF:FF:FF'), 'ff:ff:ff:ff:ff:ff' )
        self.eq( tlib.getTypeParse('inet:mac', 'FF:FF:FF:FF:FF:FF'), 'ff:ff:ff:ff:ff:ff' )
        self.eq( tlib.getTypeRepr('inet:mac', 'ff:ff:ff:ff:ff:ff'), 'ff:ff:ff:ff:ff:ff' )

    def test_datatype_inet_email(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:email', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:email', 'newp' )

        self.eq( tlib.getTypeParse('inet:email', 'ViSi@Woot.Com'), 'visi@woot.com' )

        self.eq( tlib.getTypeNorm('inet:email', 'ViSi@Woot.Com'), 'visi@woot.com' )

        self.eq( tlib.getTypeRepr('inet:email', 'visi@woot.com'), 'visi@woot.com' )

    def test_datatype_guid(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'guid', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'guid', 'newp' )

        self.eq( tlib.getTypeParse('guid', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeParse('guid', '00010203-0405-0607-0809-0A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeFrob('guid', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeNorm('guid', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeRepr('guid', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_guid_sub(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot',subof='guid')

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'woot', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'woot', 'newp' )

        self.eq( tlib.getTypeParse('woot', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeNorm('woot', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeFrob('woot', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeRepr('guid', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_hash_md5(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'hash:md5', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'hash:md5', 'newp' )

        self.eq( tlib.getTypeParse('hash:md5', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeNorm('hash:md5', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeFrob('hash:md5', '000102030405060708090A0B0C0D0E0F'), '000102030405060708090a0b0c0d0e0f')
        self.eq( tlib.getTypeRepr('hash:md5', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_inet_ipv6(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'inet:ipv6', 'newp' )
        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'inet:srv6', 'newp' )

        self.eq( tlib.getTypeParse('inet:ipv6', 'AF:00::02'), 'af::2')
        self.eq( tlib.getTypeNorm('inet:ipv6', 'AF:00::02'), 'af::2')
        self.eq( tlib.getTypeRepr('inet:ipv6', 'af::2'), 'af::2')

        if s_thishost.get('platform') != 'darwin':
            self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8::1:1:1:1:1'), '2001:db8:0:1:1:1:1:1')
            self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8:0:1:1:1:1:1'), '2001:db8:0:1:1:1:1:1')

            self.eq( tlib.getTypeFrob('inet:ipv6', '2001:db8::1:1:1:1:1'), '2001:db8:0:1:1:1:1:1')

        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8::0:1'), '2001:db8::1')
        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8:0:0:0:0:2:1'), '2001:db8::2:1')

        self.eq( tlib.getTypeNorm('inet:ipv6', '2001:db8::'), '2001:db8::')

        self.eq( tlib.getTypeRepr('inet:srv6', '[af::2]:80'), '[af::2]:80')
        self.eq( tlib.getTypeParse('inet:srv6', '[AF:00::02]:80'), '[af::2]:80')
        self.eq( tlib.getTypeNorm('inet:srv6', '[AF:00::02]:80'), '[af::2]:80')

    def test_datatype_str(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'str', 10 )

        self.eq( tlib.getTypeNorm('str','foo'), 'foo' )
        self.eq( tlib.getTypeFrob('str','foo'), 'foo' )
        self.eq( tlib.getTypeParse('str','bar'), 'bar' )

    def test_datatype_str_enums(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot',subof='str',enums='hehe,haha,hoho', lower=1)

        self.assertRaises(BadTypeValu, tlib.getTypeNorm, 'woot', 'asdf' )
        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'woot', 'asdf' )

        self.eq( tlib.getTypeNorm('woot','HeHe'), 'hehe' )
        self.eq( tlib.getTypeFrob('woot','HeHe'), 'hehe' )
        self.eq( tlib.getTypeParse('woot','HeHe'), 'hehe' )

    def test_datatype_dup(self):
        tlib = s_types.TypeLib()

        self.assertRaises(DupTypeName, tlib.addType, 'inet:port', subof='int' )

    def test_datatype_bool(self):
        tlib = s_types.TypeLib()

        self.assertRaises(BadTypeValu, tlib.getTypeParse, 'bool', 'bogus' )

        self.assertTrue( tlib.getTypeParse('bool','1') )
        self.assertTrue( tlib.getTypeParse('bool','t') )
        self.assertTrue( tlib.getTypeParse('bool','y') )
        self.assertTrue( tlib.getTypeParse('bool','TrUe') )
        self.assertTrue( tlib.getTypeParse('bool','yEs') )
        self.assertTrue( tlib.getTypeParse('bool','ON') )

        self.assertFalse( tlib.getTypeParse('bool','0') )
        self.assertFalse( tlib.getTypeParse('bool','f') )
        self.assertFalse( tlib.getTypeParse('bool','n') )
        self.assertFalse( tlib.getTypeParse('bool','FaLsE') )
        self.assertFalse( tlib.getTypeParse('bool','nO') )
        self.assertFalse( tlib.getTypeParse('bool','OFF') )

        self.assertEqual( tlib.getTypeRepr('bool',1), 'True' )
        self.assertEqual( tlib.getTypeRepr('bool',0), 'False' )

        self.assertEqual( tlib.getTypeNorm('bool',9), 1)
        self.assertEqual( tlib.getTypeNorm('bool',0), 0)

        self.assertEqual( tlib.getTypeFrob('bool',9), 1)
        self.assertFalse( tlib.getTypeFrob('bool','f') )
        self.assertFalse( tlib.getTypeFrob('bool','n') )
        self.assertFalse( tlib.getTypeFrob('bool','FaLsE') )

    def test_type_comp(self):
        tlib = s_types.TypeLib()

        tlib.addType('inet:foo:a',subof='comp',fields='fqdn,inet:fqdn|ipv4,inet:ipv4|time,time:epoch')

        jstext = '["wOOt.com","1.2.3.4","20160204080030"]'
        rawobj = ["wOOt.com","1.2.3.4","20160204080030"]

        b64t = tlib.getTypeParse('inet:foo:a',jstext)
        epoc = tlib.getTypeParse('time:epoch','20160204080030')

        item = msgunpack(base64.b64decode(b64t.encode('utf8')))

        self.assertEqual(item[0], 'woot.com')
        self.assertEqual(item[1], 0x01020304)
        self.assertEqual(item[2], epoc)

        b64t = tlib.getTypeParse('inet:foo:a',rawobj)

        item = msgunpack(base64.b64decode(b64t.encode('utf8')))

        self.assertEqual(item[0], 'woot.com')
        self.assertEqual(item[1], 0x01020304)
        self.assertEqual(item[2], epoc)

        b64t = tlib.getTypeNorm('inet:foo:a',('wOOt.com',0x01020304,epoc))

        item = msgunpack(base64.b64decode(b64t.encode('utf8')))

        self.assertEqual(item[0], 'woot.com')
        self.assertEqual(item[1], 0x01020304)
        self.assertEqual(item[2], epoc)

        b64t = tlib.getTypeNorm('inet:foo:a',b64t)

        item = msgunpack(base64.b64decode(b64t.encode('utf8')))

        self.assertEqual(item[0], 'woot.com')
        self.assertEqual(item[1], 0x01020304)
        self.assertEqual(item[2], epoc)

        rept = tlib.getTypeRepr('inet:foo:a',b64t)
        self.assertEqual( rept, '["woot.com","1.2.3.4","2016/02/04 08:00:30"]')

    def test_type_comp_chop(self):
        tlib = s_types.TypeLib()

        tlib.addType('fake:newp',subof='comp',fields='fqdn,inet:fqdn|email,inet:email')

        norm,subs = tlib.getTypeChop('fake:newp',('woot.com','visi@visi.com'))

    def test_type_comp_err(self):
        tlib = s_types.TypeLib()
        self.assertRaises( BadInfoValu, tlib.addType, 'fake:newp', subof='comp',fields='asdfqwer')

    def test_datatype_int_minmax(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot:min',subof='int',ismin=1)
        tlib.addType('woot:max',subof='int',ismax=1)

        self.eq( tlib.getTypeNorm('woot:min', 20, oldval=40), 20 )
        self.eq( tlib.getTypeNorm('woot:min', 40, oldval=20), 20 )

        self.eq( tlib.getTypeNorm('woot:max', 20, oldval=40), 40 )
        self.eq( tlib.getTypeNorm('woot:max', 40, oldval=20), 40 )

    def test_datatype_fqdn(self):
        tlib = s_types.TypeLib()

        self.eq( tlib.getTypeNorm('inet:fqdn','WOOT.COM'), 'woot.com')
        self.eq( tlib.getTypeNorm('inet:fqdn','WO-OT.COM'), 'wo-ot.com')
        self.eq( tlib.getTypeFrob('inet:fqdn','WOOT.COM'), 'woot.com')
        self.eq( tlib.getTypeFrob('inet:fqdn','WO-OT.COM'), 'wo-ot.com')
        self.eq( tlib.getTypeParse('inet:fqdn','WOOT.COM'), 'woot.com')
        self.eq( tlib.getTypeParse('inet:fqdn','WO-OT.COM'), 'wo-ot.com')

    def test_type_stor_info(self):
        tlib = s_types.TypeLib()
        self.assertRaises( BadStorValu, tlib.addType, 'fake:newp', subof='comp',fields=() )

    def test_type_pend(self):
        tlib = s_types.TypeLib()
        self.assertFalse( tlib.addType('foo',subof='bar') )
        self.assertTrue( tlib.addType('bar',subof='int') )
        self.assertIsNotNone( tlib.getDataType('foo') )

    def test_type_sepr(self):
        tlib = s_types.TypeLib()
        tlib.addType('siteuser', subof='sepr', sep='/', fields='foo,inet:fqdn|bar,inet:user')
        self.eq( tlib.getTypeNorm('siteuser','WOOT.COM/visi'), 'woot.com/visi' )
        self.eq( tlib.getTypeParse('siteuser','WOOT.COM/visi'), 'woot.com/visi' )

        norm,subs = tlib.getTypeChop('siteuser','WOOT.COM/Visi')
        self.eq(subs.get('foo'),'woot.com')
        self.eq(subs.get('bar'),'Visi')

    def test_type_str_nullval(self):
        tlib = s_types.TypeLib()
        tlib.addType('woot', subof='str', regex='^[0-9]+$', nullval='??')
        self.eq( tlib.getTypeNorm('woot','10'), '10' )
        self.eq( tlib.getTypeParse('woot','10'), '10' )

        self.eq( tlib.getTypeNorm('woot','??'), '??' )
        self.eq( tlib.getTypeParse('woot','??'), '??' )

        self.assertRaises( BadTypeValu, tlib.getTypeNorm, 'woot', 'qwer' )
        self.assertRaises( BadTypeValu, tlib.getTypeParse, 'woot', 'qwer' )

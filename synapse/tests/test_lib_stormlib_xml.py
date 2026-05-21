from unittest import mock

import synapse.exc as s_exc
import synapse.tests.utils as s_test

xml0 = '''
<?xml version="1.0"?>
<data>
    <country name="Liechtenstein">
        <rank>1</rank>
        <year>2008</year>
        <gdppc>141100</gdppc>
        <neighbor name="Austria" direction="E"/>
        <neighbor name="Switzerland" direction="W"/>
    </country>
    <country name="Singapore">
        <rank>4</rank>
        <year>2011</year>
        <gdppc>59900</gdppc>
        <neighbor name="Malaysia" direction="N"/>
    </country>
    <country name="Panama">
        <rank>68</rank>
        <year>2011</year>
        <gdppc>13600</gdppc>
        <neighbor name="Costa Rica" direction="W"/>
        <neighbor name="Colombia" direction="E"/>
    </country>
</data>
'''.strip()

def mockexc(text):
    raise Exception('newp')

class XmlTest(s_test.SynTest):

    async def test_stormlib_xml(self):

        async with self.getTestCore() as core:
            valu = await core.callStorm('''
                $retn = ()
                $root = $lib.xml.parse($xmltext)
                for $elem in $root {
                    $retn.append((
                        $elem.name,
                        $elem.attrs.name,
                        $elem.get(rank).text,
                    ))
                }
                return($retn)
            ''', opts={'vars': {'xmltext': xml0}})
            self.eq(valu, (
                ('country', 'Liechtenstein', '1'),
                ('country', 'Singapore', '4'),
                ('country', 'Panama', '68'),
            ))

            valu = await core.callStorm('''
                $retn = ()
                $root = $lib.xml.parse($xmltext)
                for $elem in $root.find(country) {
                    $retn.append((
                        $elem.name,
                        $elem.attrs.name,
                        $elem.get(rank).text,
                    ))
                }
                return($retn)
            ''', opts={'vars': {'xmltext': xml0}})
            self.eq(valu, (
                ('country', 'Liechtenstein', '1'),
                ('country', 'Singapore', '4'),
                ('country', 'Panama', '68'),
            ))

            valu = await core.callStorm('''
                $retn = ()
                $root = $lib.xml.parse($xmltext)
                for $elem in $root.find(rank) {
                    $retn.append($elem.text)
                }
                return($retn)
            ''', opts={'vars': {'xmltext': xml0}})
            self.eq(valu, ('1', '4', '68'))

            valu = await core.callStorm('''
                $retn = ()
                $root = $lib.xml.parse($xmltext)
                for $elem in $root.find(rank, nested=$lib.false) {
                    $retn.append($elem.text)
                }
                return($retn)
            ''', opts={'vars': {'xmltext': xml0}})
            self.eq(valu, ())

            valu = await core.callStorm('''
                $retn = ()
                $root = $lib.xml.parse($xmltext)
                for $elem in $root.find(rank, nested=$lib.false) {
                    $retn.append($elem.text)
                }
                return($retn)
            ''', opts={'vars': {'xmltext': xml0}})
            self.eq(valu, [])

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'bytes': b'asdf'}}
                await core.callStorm('$lib.xml.parse($bytes)', opts=opts)

            with mock.patch('xml.etree.ElementTree.fromstring', mockexc):
                with self.raises(Exception):
                    await core.callStorm('$lib.xml.parse("")', opts=opts)

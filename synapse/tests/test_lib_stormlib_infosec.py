import synapse.exc as s_exc

import synapse.tests.utils as s_test

res0 = {'ok': True, 'version': '3.1', 'score': None, 'scores': {
            'base': None, 'temporal': None, 'environmental': None}}
res1 = {'ok': True, 'version': '3.1', 'score': 10.0, 'scores': {
            'base': 10.0, 'temporal': None, 'environmental': None, 'impact': 6.0, 'exploitability': 3.9}}
res2 = {'ok': True, 'version': '3.1', 'score': 10.0, 'scores': {
            'base': 10.0, 'temporal': 10.0, 'environmental': None, 'impact': 6.0, 'exploitability': 3.9}}
res3 = {'ok': True, 'version': '3.1', 'score': 9.8, 'scores': {
            'base': 10.0, 'temporal': 10.0, 'environmental': 9.8, 'impact': 6.0, 'modifiedimpact': 5.9, 'exploitability': 3.9}}

# https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:A/AC:L/PR:H/UI:R/S:C/C:H/I:N/A:L/E:P/RL:T/RC:U/CR:H/IR:L/AR:M/MAV:X/MAC:H/MPR:L/MUI:N/MS:U/MC:H/MI:L/MA:N&version=3.1
vec4 = 'AV:A/AC:L/PR:H/UI:R/S:C/C:H/I:N/A:L/E:P/RL:T/RC:U/CR:H/IR:L/AR:M/MAV:X/MAC:H/MPR:L/MUI:N/MS:U/MC:H/MI:L/MA:N'
res4 = {'ok': True, 'version': '3.1', 'score': 5.6, 'scores': {
            'base': 6.5, 'temporal': 5.4, 'environmental': 5.6, 'impact': 4.7, 'modifiedimpact': 5.5, 'exploitability': 1.2}}

vec5 = 'AV:A/AC:L/PR:H/UI:R/S:U/C:H/I:N/A:L/E:P/RL:T/RC:U/CR:H/IR:L/AR:M/MAV:X/MAC:H/MPR:L/MUI:N/MS:C/MC:H/MI:L/MA:N'
res5 = {'ok': True, 'version': '3.1', 'score': 6.6, 'scores': {
            'base': 4.9, 'temporal': 4.1, 'environmental': 6.6, 'impact': 4.2, 'modifiedimpact': 6.0, 'exploitability': 0.7}}

# no temporal; partial environmental
# https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X&version=3.1
vec6 = 'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X'
res6 = {'ok': True, 'version': '3.1', 'score': 4.2, 'scores': {
    'base': 4.6, 'temporal': None, 'environmental': 4.2, 'impact': 3.4, 'modifiedimpact': 2.9, 'exploitability': 1.2}}

# temporal fully populated; partial environmental (only CR)
# https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/E:U/RL:O/RC:U/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X&version=3.1
vec7 = 'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/E:U/RL:O/RC:U/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X'
res7 = {'ok': True, 'version': '3.1', 'score': 3.4, 'scores': {
    'base': 4.6, 'temporal': 3.7, 'environmental': 3.4, 'impact': 3.4, 'modifiedimpact': 2.9, 'exploitability': 1.2}}

class InfoSecTest(s_test.SynTest):

    async def test_stormlib_infosec(self):

        async with self.getTestCore() as core:

            valu = await core.callStorm('''
                [ risk:vuln=* ]
                return($lib.infosec.cvss.calculate($node))
            ''')
            self.eq(res0, valu)

            valu = await core.callStorm('''
                risk:vuln
                [
                    :cvss:av=N
                    :cvss:ac=L
                    :cvss:pr=N
                    :cvss:ui=N
                    :cvss:s=C
                    :cvss:c=H
                    :cvss:i=H
                    :cvss:a=H
                ]
                return($lib.infosec.cvss.calculate($node))
            ''')
            self.eq(res1, valu)

            valu = await core.callStorm('''
                risk:vuln
                [
                    :cvss:e=H
                    :cvss:rl=U
                    :cvss:rc=C
                ]
                return($lib.infosec.cvss.calculate($node))
            ''')
            self.eq(res2, valu)

            valu = await core.callStorm('''
                risk:vuln
                [
                    :cvss:mav=N
                    :cvss:mac=L
                    :cvss:mpr=N
                    :cvss:mui=N
                    :cvss:ms=U
                    :cvss:mc=H
                    :cvss:mi=H
                    :cvss:ma=H
                    :cvss:cr=H
                    :cvss:ir=H
                    :cvss:ar=H
                ]
                return($lib.infosec.cvss.calculate($node))
            ''')

            self.eq(res3, valu)

            nodes = await core.nodes('risk:vuln')
            self.len(1, nodes)
            self.eq(9.8, nodes[0].get('cvss:score'))
            self.eq(10.0, nodes[0].get('cvss:score:base'))
            self.eq(10.0, nodes[0].get('cvss:score:temporal'))
            self.eq(9.8, nodes[0].get('cvss:score:environmental'))

            with self.raises(s_exc.BadArg):
                valu = await core.callStorm('return($lib.infosec.cvss.vectToProps(asdf))')

            with self.raises(s_exc.BadArg):
                valu = await core.callStorm('return($lib.infosec.cvss.vectToProps(foo:bar/baz:faz))')

            valu = await core.callStorm('''
                [ risk:vuln=* ]
                $lib.infosec.cvss.saveVectToNode($node, $vect)
                return($lib.infosec.cvss.calculate($node))
            ''', opts={'vars': {'vect': vec4}})

            self.eq(res4, valu)

            valu = await core.callStorm('''
                [ risk:vuln=* ]
                $lib.infosec.cvss.saveVectToNode($node, $vect)
                return($lib.infosec.cvss.calculate($node))
            ''', opts={'vars': {'vect': vec5}})

            self.eq(res5, valu)

            props = await core.callStorm('return($lib.infosec.cvss.vectToProps($vect))', opts={'vars': {'vect': vec5}})
            valu = await core.callStorm('return($lib.infosec.cvss.calculateFromProps($props))',
                                        opts={'vars': {'props': props}})
            self.eq(res5, valu)

            scmd = '''
                $props = $lib.infosec.cvss.vectToProps($vect)
                return($lib.infosec.cvss.calculateFromProps($props))
            '''

            valu = await core.callStorm(scmd, opts={'vars': {'vect': vec6}})
            self.eq(res6, valu)

            valu = await core.callStorm(scmd, opts={'vars': {'vect': vec7}})
            self.eq(res7, valu)

            vect = 'AV:A/AC:L/PR:H/UI:R/S:C/C:H/I:N/A:L/E:P/RL:T/RC:U/CR:H/IR:L/AR:M/MAV:X/MAC:H/MPR:L/MUI:N/MS:U/MC:H/MI:L/MA:N'
            valu = await core.callStorm('return($lib.infosec.cvss.vectToProps($vect))', opts={'vars': {'vect': vect}})
            self.eq(valu, {
                'cvss:av': 'A',
                'cvss:ac': 'L',
                'cvss:pr': 'H',
                'cvss:ui': 'R',
                'cvss:s': 'C',
                'cvss:c': 'H',
                'cvss:i': 'N',
                'cvss:a': 'L',
                'cvss:e': 'P',
                'cvss:rl': 'T',
                'cvss:rc': 'U',
                'cvss:cr': 'H',
                'cvss:ir': 'L',
                'cvss:ar': 'M',
                'cvss:mav': 'X',
                'cvss:mac': 'H',
                'cvss:mpr': 'L',
                'cvss:mui': 'N',
                'cvss:ms': 'U',
                'cvss:mc': 'H',
                'cvss:mi': 'L',
                'cvss:ma': 'N'
            })

            with self.raises(s_exc.BadArg):
                await core.callStorm('[ risk:vuln=* ] return($lib.infosec.cvss.calculate($node, vers=1.1.1))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('[ ps:contact=* ] return($lib.infosec.cvss.calculate($node))')

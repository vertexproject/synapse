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

VECTORS = [
    (
        'AV:A/AC:L/PR:H/UI:R/S:C/C:H/I:N/A:L/E:P/RL:T/RC:U/CR:H/IR:L/AR:M/MAV:X/MAC:H/MPR:L/MUI:N/MS:U/MC:H/MI:L/MA:N',
        {'version': '3.1', 'base': 6.5, 'temporal': 5.4, 'environmental': 5.6}
    ),
    (
        'AV:A/AC:L/PR:H/UI:R/S:U/C:H/I:N/A:L/E:P/RL:T/RC:U/CR:H/IR:L/AR:M/MAV:X/MAC:H/MPR:L/MUI:N/MS:C/MC:H/MI:L/MA:N',
        {'version': '3.1', 'base': 4.9, 'temporal': 4.1, 'environmental': 6.6}
    ),
    (
        # no temporal; partial environmental
        # https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X&version=3.1
        'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X',
        {'version': '3.1', 'base': 4.6, 'temporal': None, 'environmental': 4.2}
    ),
    (
        # temporal fully populated; partial environmental (only CR)
        # https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator?vector=AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/E:U/RL:O/RC:U/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X&version=3.1
        'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/E:U/RL:O/RC:U/CR:L/IR:X/AR:X/MAV:X/MAC:X/MPR:X/MUI:X/MS:X/MC:X/MI:X/MA:X',
        {'version': '3.1', 'base': 4.6, 'temporal': 3.7, 'environmental': 3.4}
    ),
    (
        '(AV:L/AC:L/Au:M/C:P/I:C/A:N/E:ND/RL:TF/RC:ND/CDP:N/TD:ND/CR:ND/IR:ND/AR:ND)',
        {'version': '2', 'base': 5.0, 'temporal': 4.5, 'environmental': 4.5}
    ),
    (
        '(AV:L/AC:L/Au:M/C:P/I:C/A:N/E:ND/RL:OF/RC:ND/CDP:N/TD:ND/CR:ND/IR:ND/AR:ND)',
        {'version': '2', 'base': 5.0, 'temporal': 4.4, 'environmental': 4.3}
    ),
    (
        'AV:N/AC:L/Au:N/C:N/I:N/A:C/E:F/RL:OF/RC:C/AR:H/CR:M/IR:M/CDP:H/TD:H',
        {'version': '2', 'base': 7.8, 'temporal': 6.4, 'environmental': 9.2}
    ),
    (
        'CVSS2#AV:L/AC:L/Au:M/C:P/I:C/A:N',
        {'version': '2', 'base': 5.0, 'temporal': None, 'environmental': 5.0}
    ),
    (
        '(AV:L/AC:L/Au:M/C:P/I:C/A:N)',
        {'version': '2', 'base': 5.0, 'temporal': None, 'environmental': 5.0}
    ),
    (
        'AV:L/AC:L/Au:M/C:P/I:C/A:N',
        {'version': '2', 'base': 5.0, 'temporal': None, 'environmental': 5.0}
    ),
    (
        'CVSS:3.0/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',
        {'version': '3.0', 'base': 4.6, 'temporal': None, 'environmental': 4.6}
    ),
    (
        'CVSS:3.1/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',
        {'version': '3.1', 'base': 4.6, 'temporal': None, 'environmental': 4.6}
    ),
    (
        '(AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L)',
        {'version': '3.1', 'base': 4.6, 'temporal': None, 'environmental': 4.6}
    ),
    (
        'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',
        {'version': '3.1', 'base': 4.6, 'temporal': None, 'environmental': 4.6}
    ),
    (
        'AV:N/AC:H/PR:H/UI:R/S:C/C:N/I:N/A:N/E:H/RL:U/RC:C/CR:H/IR:H/AR:H/MAV:A/MAC:H/MPR:H/MUI:R/MS:C/MC:N/MI:N/MA:N',
        {'version': '3.1', 'base': 0.0, 'temporal': 0.0, 'environmental': 0.0}
    ),
    (
        '(AV:N/AC:L/Au:N/C:N/I:N/A:N/E:U/RL:OF/RC:UC/CDP:H/TD:H/CR:H/IR:H/AR:H)',
        {'version': '2', 'base': 0.0, 'temporal': 0.0, 'environmental': 5.0}
    ),
    (
        '(AV:N/AC:L/Au:N/C:N/I:N/A:N/CDP:H/TD:H/CR:H/IR:H/AR:H)',
        {'version': '2', 'base': 0.0, 'temporal': None, 'environmental': 5.0}
    )
]

VECTORS_BAD_VERSION = [
    ('CVSS2#AV:L/AC:L/C:P/I:C/A:N', '3.1'),
    ('(AV:L/AC:L/Au:M/I:C/A:N)', '3.1'),
    ('AV:L/AC:L/Au:M/C:P/A:N', '3.1'),
    ('CVSS:3.0/AV:N/AC:H/UI:R/S:U/C:L/I:L/A:L', '2'),
    ('CVSS:3.1/AV:N/AC:H/PR:L/S:U/C:L/I:L/A:L', '2'),
    ('(AV:N/AC:H/PR:L/UI:R/S:U/I:L/A:L)', '2'),
    ('AV:N/PR:L/UI:R/S:U/C:L/I:L/A:L', '2'),
]

VECTORS_MISSING_MANDATORY = [
    'CVSS2#AV:L/AC:L/C:P/I:C/A:N',
    '(AV:L/AC:L/Au:M/I:C/A:N)',
    'AV:L/AC:L/Au:M/C:P/A:N',
    'CVSS:3.0/AV:N/AC:H/UI:R/S:U/C:L/I:L/A:L',
    'CVSS:3.1/AV:N/AC:H/PR:L/S:U/C:L/I:L/A:L',
    '(AV:N/AC:H/PR:L/UI:R/S:U/I:L/A:L)',
    'AV:N/PR:L/UI:R/S:U/C:L/I:L/A:L',
]
VECTORS_INVALID_VALUE = [
    'CVSS2#AV:L/AC:L/Au:Z/C:P/I:C/A:N',
    '(AV:L/AC:L/Au:M/C:Z/I:C/A:N)',
    'AV:L/AC:L/Au:M/C:P/I:Z/A:N',
    'CVSS:3.0/AV:N/AC:H/PR:Z/UI:R/S:U/C:L/I:L/A:L',
    'CVSS:3.1/AV:N/AC:Z/PR:L/UI:R/S:U/C:L/I:L/A:L',
    '(AV:N/AC:H/PR:L/UI:Z/S:U/C:L/I:L/A:L)',
    'AV:N/AC:H/PR:L/UI:R/S:Z/C:L/I:L/A:L',
]
VECTORS_DUPLICATE_METRIC = [
    'CVSS2#AV:L/AC:L/Au:M/Au:M/C:P/I:C/A:N',
    '(AV:L/AC:L/Au:M/C:P/C:P/I:C/A:N)',
    'AV:L/AC:L/Au:M/C:P/I:C/I:C/A:N',
    'CVSS:3.0/AV:N/AC:H/PR:L/PR:L/UI:R/S:U/C:L/I:L/A:L',
    'CVSS:3.1/AV:N/AC:H/PR:L/UI:R/UI:R/S:U/C:L/I:L/A:L',
    '(AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L/A:L)',
    'AV:N/AC:H/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',
]

VECTORS_MALFORMED = [
    # Double /
    'CVSS2#AV:L//AC:L/Au:M/C:P/I:C/A:N',
    '(AV:L/AC:L//Au:M/C:P/I:C/A:N)',
    'AV:L/AC:L//Au:M/C:P/I:C/A:N',
    'CVSS:3.0//AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',
    'CVSS:3.1/AV:N//AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',
    '(AV:N/AC:H/PR:L//UI:R/S:U/C:L/I:L/A:L)',
    'AV:N/AC:H/PR:L//UI:R/S:U/C:L/I:L/A:L',

    # Double :
    'CVSS2#AV:L/AC::L/Au:M/C:P/I:C/A:N',
    '(AV:L/AC:L/Au:M/C::P/I:C/A:N)',
    'AV:L/AC:L/Au:M/C:P/I::C/A:N',
    'CVSS:3.0/AV:N/AC:H/PR::L/UI:R/S:U/C:L/I:L/A:L',
    'CVSS:3.1/AV:N/AC:H/PR:L/UI::R/S:U/C:L/I:L/A:L',
    '(AV:N/AC:H/PR:L/UI:R/S:U/C:L/I::L/A:L)',
    'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A::L',

    # Missing /
    'CVSS2#AV:LAC:L/Au:M/C:P/I:C/A:N',
    '(AV:L/AC:L/Au:MC:P/I:C/A:N)',
    'AV:L/AC:L/Au:M/C:PI:C/A:N',
    'CVSS:3.0/AV:N/AC:H/PR:LUI:R/S:U/C:L/I:L/A:L',
    'CVSS:3.1/AV:N/AC:H/PR:L/UI:RS:U/C:L/I:L/A:L',
    '(AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:LA:L)',
    'AV:NAC:H/PR:L/UI:R/S:U/C:L/I:L/A:L',

    # Missing :
    'CVSS2#AV:L/ACL/Au:M/C:P/I:C/A:N',
    '(AV:L/AC:L/Au:M/CP/I:C/A:N)',
    'AV:L/AC:L/Au:M/C:P/IC/A:N',
    'CVSS:3.0/AV:N/AC:H/PRL/UI:R/S:U/C:L/I:L/A:L',
    'CVSS:3.1/AV:N/AC:H/PR:L/UIR/S:U/C:L/I:L/A:L',
    '(AV:N/AC:H/PR:L/UI:R/S:U/C:L/IL/A:L)',
    'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/AL',
]

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

            vect = f'CVSS:3.1/{vec7}'
            valu = await core.callStorm(scmd, opts={'vars': {'vect': vect}})
            self.eq(res7, valu)

            vect = f'CVSS:3.0/{vec7}'
            with self.raises(s_exc.BadArg):
                await core.callStorm(scmd, opts={'vars': {'vect': vect}})

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

            self.len(1, await core.nodes('[ risk:vuln=* :cvss:av=P :cvss:mav=P ]'))

            with self.raises(s_exc.BadArg):
                await core.callStorm('[ risk:vuln=* ] return($lib.infosec.cvss.calculate($node, vers=1.1.1))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('[ ps:contact=* ] return($lib.infosec.cvss.calculate($node))')

    async def test_stormlib_infosec_vectToScore(self):

        async with self.getTestCore() as core:

            cmd = 'return($lib.infosec.cvss.vectToScore($vect))'
            vercmd = 'return($lib.infosec.cvss.vectToScore($vect, $vers))'

            for vect, score in VECTORS:
                valu = await core.callStorm(cmd, opts={'vars': {'vect': vect}})
                self.eq(score, valu)

            # test for invalid version being specified
            with self.raises(s_exc.BadArg):
                await core.callStorm(vercmd, opts={'vars': {'vect': 'DOESNT_MATTER', 'vers': '1.0'}})

            # test for vector/version mismatches
            for vect, vers in VECTORS_BAD_VERSION:
                with self.raises(s_exc.BadDataValu) as exc:
                    await core.callStorm(vercmd, opts={'vars': {'vect': vect, 'vers': vers}})

            # test for missing mandatory metrics
            for vect in VECTORS_MISSING_MANDATORY:
                with self.raises(s_exc.BadDataValu):
                    await core.callStorm(cmd, opts={'vars': {'vect': vect}})

            # test for invalid metric values
            for vect in VECTORS_INVALID_VALUE:
                with self.raises(s_exc.BadDataValu):
                    await core.callStorm(cmd, opts={'vars': {'vect': vect}})

            # test for duplicate metrics
            for vect in VECTORS_DUPLICATE_METRIC:
                with self.raises(s_exc.BadDataValu):
                    await core.callStorm(cmd, opts={'vars': {'vect': vect}})

            # test for malformed vector string
            for vect in VECTORS_MALFORMED:
                with self.raises(s_exc.BadDataValu):
                    await core.callStorm(cmd, opts={'vars': {'vect': vect}})

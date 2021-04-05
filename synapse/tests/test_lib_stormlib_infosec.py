import os
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

res0 = {'ok': True, 'version': '3.1', 'score': None, 'scores': {
            'base': None, 'temporal': None, 'environmental': None}}
res1 = {'ok': True, 'version': '3.1', 'score': 10.0, 'scores': {
            'base': 10.0, 'temporal': None, 'environmental': None, 'impact': 6.1, 'exploitability': 3.9}}
res2 = {'ok': True, 'version': '3.1', 'score': 10.0, 'scores': {
            'base': 10.0, 'temporal': 10.0, 'environmental': None, 'impact': 6.1, 'exploitability': 3.9}}
res3 = {'ok': True, 'version': '3.1', 'score': 9.8, 'scores': {
            'base': 10.0, 'temporal': 10.0, 'environmental': 9.8, 'impact': 6.1, 'modifiedimpact': 5.9, 'exploitability': 3.9}}

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

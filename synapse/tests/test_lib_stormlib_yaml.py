import synapse.exc as s_exc
import synapse.tests.utils as s_test

yaml00 = '''
foo: bar
baz: faz
'''

class YamlTest(s_test.SynTest):

    async def test_stormlib_yaml(self):
        async with self.getTestCore() as core:
            valu = await core.callStorm('''
                return($lib.yaml.save((hehe, haha, hoho)))
            ''')
            self.eq(valu, '- hehe\n- haha\n- hoho\n')

            valu = await core.callStorm('''
                return($lib.yaml.load($yaml00))
            ''', opts={'vars': {'yaml00': yaml00}})
            self.eq(valu, {'foo': 'bar', 'baz': 'faz'})

import synapse.common as s_common
import synapse.tests.utils as s_t_utils

class MathTest(s_t_utils.SynTest):

    async def test_model_math_algo(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ math:algorithm=*
                    :name="  ImPHaSH "
                    :created=20120202
                    :type=hash.imports
                    :desc="Import Hashes!"
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'imphash')
            self.propeq(nodes[0], 'type', 'hash.imports.')
            self.propeq(nodes[0], 'created', 1328140800000000)
            self.propeq(nodes[0], 'desc', "Import Hashes!")
            self.len(1, await core.nodes('math:algorithm -> math:algorithm:type:taxonomy'))

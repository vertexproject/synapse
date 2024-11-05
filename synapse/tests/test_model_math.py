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
            self.eq('imphash', nodes[0].get('name'))
            self.eq('hash.imports.', nodes[0].get('type'))
            self.eq(1328140800000, nodes[0].get('created'))
            self.eq("Import Hashes!", nodes[0].get('desc'))
            self.len(1, await core.nodes('math:algorithm -> math:algorithm:type:taxonomy'))

import synapse.tests.utils as s_t_utils

import synapse.lib.hashitem as s_hashitem

class HashItemTest(s_t_utils.SynTest):

    def test_lib_hashitem(self):
        x = {
            'foo': ['bar', 'baz'],
            'boing': ('gniob', 'boing'),

            'lol': 10,
            'hehe': 'haha',
            'gronk': {
                'hurr': 30,
                'durr': 40,
            },
        }

        y = {
            'boing': ('gniob', 'boing'),
            'foo': ['bar', 'baz'],

            'lol': 10,
            'gronk': {
                'durr': 40,
                'hurr': 30,
            },
            'hehe': 'haha',
        }

        self.eq(s_hashitem.hashitem(x), s_hashitem.hashitem(y))

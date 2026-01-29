import synapse.lib.storm_format as s_storm_format
import synapse.lib.parser as s_parser

from synapse.tests.test_lib_grammar import Queries

def test_highlight_storm():

    for _, query in enumerate(Queries):
        s_storm_format.highlight_storm(s_parser.LarkParser, query)

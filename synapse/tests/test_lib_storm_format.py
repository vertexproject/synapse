import synapse.lib.storm_format as s_storm_format
import synapse.lib.parser as s_parser

from synapse.tests.test_lib_grammar import _Queries

def test_highlight_storm():

    for _, query in enumerate(_Queries):
        s_storm_format.highlight_storm(s_parser.QueryParser, query)

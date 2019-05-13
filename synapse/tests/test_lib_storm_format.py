import lark  # type: ignore
import synapse.lib.datfile as s_datfile
import synapse.lib.storm_format as s_storm_format
import synapse.lib.grammar as s_grammar

from synapse.tests.test_lib_grammar import _Queries

def test_highlight_storm():

    for i, query in enumerate(_Queries):
        s_storm_format.highlight_storm(s_grammar.CmdrParser, query)

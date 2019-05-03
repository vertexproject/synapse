import lark  # type: ignore
import synapse.lib.datfile as s_datfile
import synapse.tools.storm_format as st_storm_format

def test_highlight_storm():
    from synapse.tests.test_lib_syntax2 import _Queries

    with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
        grammar = larkf.read().decode()

    parser = lark.Lark(grammar, start='query', propagate_positions=True, keep_all_tokens=True)

    for i, query in enumerate(_Queries):
        st_storm_format.highlight_storm(parser, query)

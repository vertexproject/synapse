
from synapse.tools.dmon import getArgParser
import pytest


class TestArgParser(object):
    @pytest.mark.parametrize('level', ['debug', 'info', 'warning', 'error', 'critical'])
    def test_getArgParser_logLevel(self, level):
        p = getArgParser()
        p.parse_args(['--log-level', level])

    @pytest.mark.parametrize('level', ['all', 'notice'])
    def test_getArgParser_logLevel_exception(self, level):
        with pytest.raises(SystemExit):
            p = getArgParser()
            p.parse_args(['--log-level', level])

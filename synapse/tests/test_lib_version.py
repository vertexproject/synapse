"""
synapse - test_lib_version.py
Created on 10/6/17.
"""

import synapse.lib.version as s_version

from synapse.tests.common import *

class VersionTest(SynTest):

    def test_version_basics(self):
        self.isinstance(s_version.version, tuple)
        self.len(3, s_version.version)
        for v in s_version.version:
            self.isinstance(v, int)

        self.isinstance(s_version.verstring, str)
        tver = tuple([int(p) for p in s_version.verstring.split('.')])
        self.eq(tver, s_version.version)

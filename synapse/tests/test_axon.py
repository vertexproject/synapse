import io
import logging

import synapse.axon as s_axon
import synapse.common as s_common
#import synapse.daemon as s_daemon
#import synapse.telepath as s_telepath

#import synapse.lib.tufo as s_tufo
#import synapse.lib.service as s_service

from synapse.tests.common import *

asdfbyts = b'asdfasdf'
craphash = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
asdfhash = '6a204bd89f3c8348afd5c77c717a097a'
asdfhash_iden = '1c753abfe85b4cbe46584fa5b1834fa4'

logger = logging.getLogger(__name__)

class AxonTest(SynTest):

    def test_axon_base(self):

        with self.getTestDir() as dirn:

            conf = {'dir': s_common.gendir(dirn, 'axon')}

            with s_axon.Axon(conf) as axon:

                self.false(axon.has('md5', asdfhash))

    #def test_axon_sync(self):

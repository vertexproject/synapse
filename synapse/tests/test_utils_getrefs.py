import os
import pathlib

import vcr

from unittest import mock

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.config as s_config

import synapse.tests.utils as s_utils
import synapse.tests.files as s_test_files

import synapse.utils.getrefs as s_getrefs

CORE_URL = 'http://raw.githubusercontent.com/oasis-open/cti-stix2-json-schemas/stix2.1/schemas/common/core.json'

class TestUtilsGetrefs(s_utils.SynTest):

    def getVcr(self):
        fn = f'{self.__class__.__name__}.{self._testMethodName}.yaml'
        fp = os.path.join(s_test_files.ASSETS, fn)
        myvcr = vcr.VCR(decode_compressed_response=True)
        cm = myvcr.use_cassette(fp)
        return cm

    def test_basics(self):

        args = s_getrefs.parse_args([
            s_data.path('attack-flow', 'attack-flow-schema-2.0.0.json')
        ])

        with self.getLoggerStream('synapse.utils.getrefs') as stream:
            s_getrefs.main(args)

        stream.seek(0)
        mesgs = stream.read()
        mesg = f'Schema {CORE_URL} already exists in local cache, skipping.'
        self.isin(mesg, mesgs)
        self.notin('Downloading schema from', mesgs)

        with self.raises(s_exc.BadUrl):
            s_getrefs.download_refs_handler('http://[/newp')

        with self.raises(s_exc.BadArg):
            s_getrefs.download_refs_handler('http://raw.githubusercontent.com/../../attack-flow/attack-flow-schema-2.0.0.json')

        with self.getTestDir(copyfrom=s_getrefs.BASEDIR) as dirn:

            filename = pathlib.Path(s_common.genpath(
                dirn,
                'raw.githubusercontent.com',
                'oasis-open',
                'cti-stix2-json-schemas',
                'stix2.1',
                'schemas',
                'common',
                'core.json'
            ))

            self.true(filename.exists())
            filename.unlink()
            self.false(filename.exists())

            # Clear the cached validator funcs so the ref handlers in s_getrefs get called
            s_config._JsValidators = {}

            with self.getLoggerStream('synapse.utils.getrefs') as stream:
                with mock.patch('synapse.utils.getrefs.BASEDIR', dirn):
                    with self.getVcr():
                        s_getrefs.main(args)

            stream.seek(0)
            mesgs = stream.read()
            mesg = f'Downloading schema from {CORE_URL}.'
            self.true(filename.exists())
            self.isin(mesg, mesgs)
            self.notin(f'Schema {CORE_URL} already exists in local cache, skipping.', mesgs)

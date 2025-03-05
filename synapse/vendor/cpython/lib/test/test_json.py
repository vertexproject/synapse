# From the python source, tests/test_json/test_unicode.py does not have a
# direct test for detect_encoding. It instead tests the various encoding
# schemes in test_bytes_decode, which uses the detection in json.loads().
# Since there is not a standalone test to vendor, we have written a simple
# test on its own.

import synapse.vendor.cpython.lib.json as v_json

import synapse.vendor.utils as s_v_utils

class JsonVendorTest(s_v_utils.VendorTest):
    def test_json_detect_encoding(self):

        ENCODINGS = (
            'utf-8', 'utf-8-sig',
            'utf-16', 'utf-16-le', 'utf-16-be',
            'utf-32', 'utf-32-le', 'utf-32-be',
        )

        for encoding in ENCODINGS:
            self.assertEqual(encoding, v_json.detect_encoding('a'.encode(encoding)))
            self.assertEqual(encoding, v_json.detect_encoding('ab'.encode(encoding)))

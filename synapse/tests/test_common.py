import unittest

from synapse.common import *

class CommonTest(unittest.TestCase):

    def test_common_vertup(self):
        self.assertEqual( vertup('1.3.30'), (1,3,30) )
        self.assertTrue( vertup('30.40.50') > (9,0) )

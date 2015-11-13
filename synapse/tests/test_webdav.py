import io
import unittest

import synapse.lib.webdav as s_webdav

class DavTest(unittest.TestCase):

    def test_pathnode_namedpath(self):
        root = s_webdav.PathNode()
        node = root.addNamedPath('/foo/bar/baz')

        self.assertIsNotNone(node)
        self.assertEqual( node.getBaseName(), 'baz')

    def test_pathnode_regex(self):
        root = s_webdav.PathNode()
        node = root.addNamedPath('/foo')
        renode = node.addSubNode( s_webdav.RegexNode('^bar.*') )

        dyns,hitnode = root.getPathNode('/foo/baryermom')

        self.assertEqual( tuple(dyns), ('baryermom',))
        self.assertEqual( hitnode, renode )

    def test_pathnode_file(self):
        root = s_webdav.PathNode()
        node = root.addNamedPath('/foo')

        fd = io.BytesIO(b'asdf')
        finode = node.addSubNode( s_webdav.FileNode('bar',fd) )

        dyns,node = root.getPathNode('/foo/bar')
        self.assertEqual( node.read(dyns), b'asdf') 

        dyns,node = root.getPathNode('/foo')

        nodes = node.getSubNodes()
        self.assertEqual( len(nodes), 1 )
        self.assertEqual( nodes[0].getBaseName(), 'bar') 

    # TODO: actual http server based tests using requests module.


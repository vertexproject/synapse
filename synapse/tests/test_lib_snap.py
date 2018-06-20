import os
import synapse.exc as s_exc
import synapse.lib.auth as s_auth
import synapse.tests.common as s_t_common

class SnapTest(s_t_common.SynTest):

    def test_stor(self):
        self.skip('FIXME: stor buid issue')
        with self.getTestCore() as core:

            # Bulk
            with core.snap() as snap:
                snap.bulk = True
                self.eq(snap.bulksops, ())

                self.none(snap.stor((1,)))
                self.eq(snap.bulksops, (1,))

                self.none(snap.stor((2,)))
                self.eq(snap.bulksops, (1, 2,))

    def test_addNode_noperms(self):
        form = 'teststr'
        valu = 'cool'

        with self.getTestCore() as core:

            with core.snap() as snap:

                with self.getTestDir() as dirn:

                    with s_auth.Auth(dirn) as auth:

                        user = auth.addUser('hatguy')
                        snap.setUser(user)

                        self.true(snap.strict)  # Following assertions based on snap.strict being true
                        self.raises(s_exc.AuthDeny, snap.addNode, form, valu)

                        snap.strict = False
                        self.none(snap.addNode(form, valu))

    def test_addNodes(self):
        with self.getTestCore() as core:
            with core.snap() as snap:
                ndefs = ()
                self.len(0, list(snap.addNodes(ndefs)))

                ndefs = (
                    (('teststr', 'hehe'), {'props': {'.created': 5, 'tick': 3}, 'tags': {'cool': (1, 2)}}, ),
                )
                result = list(snap.addNodes(ndefs))
                self.len(1, result)

                node = result[0]
                self.eq(node.props.get('tick'), 3)
                self.ge(node.props.get('.created'), 5)
                self.eq(node.tags.get('cool'), (1, 2))

                with self.getTestDir() as dirn:
                    with s_auth.Auth(dirn) as auth:
                        user = auth.addUser('hatguy')
                        user.addRule((True, ('node:add', 'teststr')))
                        snap.setUser(user)

                        ndefs = (
                            (('teststr', 'haha'), {}, ),   # allowed
                            (('testauto', 'hoho'), {}, ),  # not allowed
                            (('teststr', 'huhu'), {}, ),   # allowed
                        )

                        # Demonstrate what happens when individual call to addNode fails during addNodes
                        with self.raises(s_exc.AuthDeny):
                            result = list(snap.addNodes(ndefs))

                        self.nn(snap.getNodeByNdef(('teststr', 'haha')))
                        self.none(snap.getNodeByNdef(('testauto', 'hoho')))
                        # missing because call fails because in strict mode
                        self.none(snap.getNodeByNdef(('teststr', 'huhu')))

                        # Try again with strict mode disabled
                        snap.strict = False
                        ndefs = (
                            (('teststr', 'foo'), {}, ),   # allowed
                            (('testauto', 'bar'), {}, ),  # not allowed, still won't go through even if strict is false
                            (('testtime', 'baz'), {}, ),   # invalid
                            (('teststr', 'faz'), {}, ),   # allowed
                        )

                        result = list(snap.addNodes(ndefs))
                        self.len(4, result)
                        self.nn(snap.getNodeByNdef(('teststr', 'foo')))
                        self.none(snap.getNodeByNdef(('testauto', 'bar')))
                        self.none(snap.getNodeByNdef(('testtime', 'baz')))
                        self.nn(snap.getNodeByNdef(('teststr', 'faz')))

    def test_cortex_lift_layers_bad_filter(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result
        '''
        with self.getTestCore() as core1:
            node = (('inet:ipv4', 1), {'props': {'asn': 42, '.seen': (1, 2)}, 'tags': {'woot': (1, 2)}})
            nodes_core1 = list(core1.addNodes([node]))

            layerfn = os.path.join(core1.dirn, 'layers', 'default')
            with self.getTestCore(conf={'layers': [layerfn]}) as core, core.snap() as snap:
                # Basic sanity check
                nodes = list(snap.getNodesBy('inet:ipv4', 1))
                self.len(1, nodes)
                nodes = list(snap.getNodesBy('inet:ipv4.seen', 1))
                self.len(1, nodes)
                self.eq(nodes_core1[0].pack(), nodes[0].pack())
                nodes = list(snap.getNodesBy('inet:ipv4#woot', 1))
                self.len(1, nodes)
                nodes = list(snap.getNodesBy('inet:ipv4#woot', 99))
                self.len(0, nodes)

                # Now change asn in the "higher" layer
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 43, '.seen': (3, 4)}, 'tags': {'woot': (3, 4)}})
                nodes = list(snap.addNodes([changed_node]))
                # Lookup by prop
                nodes = list(snap.getNodesBy('inet:ipv4:asn', 42))
                self.len(0, nodes)

                # Lookup by univ prop
                nodes = list(snap.getNodesBy('inet:ipv4.seen', 1))
                self.len(0, nodes)

                # Lookup by formtag
                nodes = list(snap.getNodesBy('inet:ipv4#woot', 1))
                self.len(0, nodes)

                # Lookup by tag
                nodes = list(snap.getNodesBy('#woot', 1))
                self.len(0, nodes)

    def test_cortex_lift_layers_dup(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        with self.getTestCore() as core1:
            node = (('inet:ipv4', 1), {'props': {'asn': 42}})
            nodes_core1 = list(core1.addNodes([node]))

            layerfn = os.path.join(core1.dirn, 'layers', 'default')
            with self.getTestCore(conf={'layers': [layerfn]}) as core, core.snap() as snap:
                # Basic sanity check
                nodes = list(snap.getNodesBy('inet:ipv4', 1))
                self.len(1, nodes)
                self.eq(nodes_core1[0].pack(), nodes[0].pack())

                # Now set asn in the "higher" layer to the same (by changing it, then changing it back)
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 43}})
                nodes = list(snap.addNodes([changed_node]))
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 42}})
                nodes = list(snap.addNodes([changed_node]))
                nodes = list(snap.getNodesBy('inet:ipv4:asn', 42))
                self.len(1, nodes)

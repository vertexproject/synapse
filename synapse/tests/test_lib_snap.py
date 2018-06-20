import synapse.exc as s_exc
import synapse.lib.auth as s_auth
import synapse.tests.common as s_t_common

class SnapTest(s_t_common.SynTest):

    def test_stor(self):
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

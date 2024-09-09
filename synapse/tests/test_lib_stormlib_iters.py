from unittest import mock

import synapse.exc as s_exc

import synapse.tests.utils as s_test

import synapse.lib.stormlib.iters as s_stormlib_iters

class StormLibItersTest(s_test.SynTest):

    async def test_stormlib_iters_zip(self):

        async with self.getTestCore() as core:

            async with s_test.matchContexts(self):

                q = '''
                for $item in $lib.iters.zip((1,2,3), (4,5,6), (7,8,9)) {
                    $lib.print($item)
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormIsInPrint("['2', '5', '8']", msgs)
                self.stormIsInPrint("['3', '6', '9']", msgs)

                q = '''
                for $item in $lib.iters.zip((1,2,3), (4,5,6), (7,8)) {
                    $lib.print($item)
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormIsInPrint("['2', '5', '8']", msgs)
                self.stormNotInPrint("['3', '6']", msgs)

                q = '''
                function nodes() {
                    [ it:dev:str=4 it:dev:str=5 it:dev:str=6 ]
                }
                function emitter() {
                    emit 7
                    emit 8
                    emit 9
                }
                for ($a, $b, $c) in $lib.iters.zip((1,2,3), $nodes(), $emitter()) {
                    $lib.print(($a, $b.0.repr(), $c))
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormIsInPrint("['2', '5', '8']", msgs)
                self.stormIsInPrint("['3', '6', '9']", msgs)

                q = '''
                function nodes() {
                    [ it:dev:str=4 it:dev:str=5 it:dev:str=6 ]
                }
                function emitter() {
                    emit 7
                    emit 8
                    emit 9
                }
                for ($a, $b, $c) in $lib.iters.zip((1,2,3), $nodes(), $emitter()) {
                    $lib.print(($a, $b.0.repr(), $c))
                    $lib.raise(foo, bar)
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormNotInPrint("['2', '5', '8']", msgs)
                self.stormNotInPrint("['3', '6', '9']", msgs)

                q = '''
                function nodes() {
                    [ it:dev:str=4  it:dev:str=5 it:dev:str=6]
                }
                function emitter() {
                    emit 7
                    $lib.raise(foo, bar)
                    emit 8
                    emit 9
                }
                for ($a, $b, $c) in $lib.iters.zip((1,2,3), $nodes(), $emitter()) {
                    $lib.print(($a, $b.0.repr(), $c))
                }
                '''
                msgs = await core.stormlist(q)
                self.stormIsInPrint("['1', '4', '7']", msgs)
                self.stormNotInPrint("['2', '5', '8']", msgs)
                self.stormNotInPrint("['3', '6', '9']", msgs)

                err = "$lib.iters.zip() encountered errors in 1 iterators during iteration: (foo: bar)"
                self.stormIsInErr(err, msgs)

                async def boom(self, genr):
                    print(newp)
                    yield True

                with mock.patch.object(s_stormlib_iters.LibIters, 'enum', boom):
                    q = '''
                    function e1() {
                        $lib.raise(foo, bar)
                    }
                    function e2() {
                        $lib.print($newp)
                    }
                    for ($a, $b, $c) in $lib.iters.zip($e1(), $e2(), $lib.iters.enum($e2())) {
                    }
                    '''
                    msgs = await core.stormlist(q)
                    errs = (
                        "$lib.iters.zip() encountered errors in 3 iterators during iteration: ",
                        "(foo: bar)",
                        "(NoSuchVar: Missing variable: newp)",
                        "(NameError: name 'newp' is not defined)",
                    )
                    for errchunk in errs:
                        self.stormIsInErr(errchunk, msgs)

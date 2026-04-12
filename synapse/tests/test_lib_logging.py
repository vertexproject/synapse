import asyncio
import logging

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.logging as s_logging

import synapse.tests.utils as s_test

logger = logging.getLogger(__name__)

class LoggingTest(s_test.SynTest):

    async def test_lib_logging(self):

        s_logging.setup()

        self.eq(10, s_logging.normLogLevel(' 10 '))
        self.eq(10, s_logging.normLogLevel(10))
        self.eq(20, s_logging.normLogLevel(' inFo\n'))

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel(100)

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel('BEEP')

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel('12')

        with self.raises(s_exc.BadArg):
            s_logging.normLogLevel({'key': 'newp'})

        s_logging.reset()

        self.none(s_logging.StreamHandler._pump_task)
        self.none(s_logging.StreamHandler._pump_event)
        self.len(0, s_logging.StreamHandler._logs_fifo)
        self.len(0, s_logging.StreamHandler._text_todo)
        self.len(0, s_logging.StreamHandler._logs_todo)

        with self.getLoggerStream('synapse.tests.test_lib_logging') as stream:

            try:
                try:
                    raise s_exc.SynErr(mesg='omg')
                except Exception as e1:
                    e1.add_note('inner note')
                    raise s_exc.NoSuchType(mesg='woot') from e1
            except Exception as e0:
                e0.add_note('outer note')
                logger.exception(e0)

            mesg = stream.jsonlines()[0]
            self.eq(mesg['error']['code'], 'NoSuchType')
            self.eq(mesg['error']['notes'], ('outer note',))
            self.eq(mesg['error']['cause']['code'], 'SynErr')
            self.eq(mesg['error']['cause']['notes'], ('inner note',))

            self.none(mesg['error'].get('context'))

            stream.clear()

            try:
                try:
                    raise s_exc.SynErr(mesg='omg')
                except Exception as e1:
                    e1.add_note('inner note')
                    raise s_exc.NoSuchType(mesg='woot')
            except Exception as e0:
                e0.add_note('outer note')
                logger.exception(e0)

            mesg = stream.jsonlines()[0]
            self.eq(mesg['error']['code'], 'NoSuchType')
            self.eq(mesg['error']['notes'], ('outer note',))
            self.eq(mesg['error']['context']['code'], 'SynErr')
            self.eq(mesg['error']['context']['notes'], ('inner note',))

    async def test_lib_logging_storm_complex_types(self):

        async with self.getTestCore() as core:

            # list: repr() keeps it serializable even though List is not JSON-native
            exc = None
            try:
                await core.nodes('$items = ((10), (5))\n$z = ($items.0 / 0)\n')
            except Exception as e:
                exc = e

            self.nn(exc)
            info = s_logging.excinfo(exc)
            storm = info.get('storm')
            self.nn(storm)
            self.isin('$items', storm['vars'])
            self.eq(storm['vars']['$items'], repr([10, 5]))

            # dict: repr() keeps it serializable even though Dict is not JSON-native
            exc = None
            try:
                await core.nodes('$d = ({"a": (10)})\n$z = ($d.a / 0)\n')
            except Exception as e:
                exc = e

            self.nn(exc)
            info = s_logging.excinfo(exc)
            storm = info.get('storm')
            self.nn(storm)
            self.isin('$d', storm['vars'])
            self.isin("'a'", storm['vars']['$d'])

            # http response: repr() keeps it serializable even though HttpResp is not JSON-native
            addr, port = await core.addHttpsPort(0)
            core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
            url = f'https://127.0.0.1:{port}/api/v0/test'

            exc = None
            try:
                q = f'$resp = $lib.inet.http.get("{url}", ssl_verify=$lib.false)\n$z = ($resp.code / 0)\n'
                await core.nodes(q)
            except Exception as e:
                exc = e

            self.nn(exc)
            info = s_logging.excinfo(exc)
            storm = info.get('storm')
            self.nn(storm)
            self.isin('$resp', storm['vars'])
            self.isin("'code'", storm['vars']['$resp'])

    async def test_lib_logging_storm_pkg(self):

        # package with two modules: testpkg.math defines divcheck(), testpkg.ops calls it
        pkg = {
            'name': 'testpkg',
            'version': (0, 0, 1),
            'modules': (
                {
                    'name': 'testpkg.math',
                    'storm': 'function divcheck(a, b) { $result = ($a / $b) return($result) }',
                },
                {
                    'name': 'testpkg.ops',
                    'storm': 'function run(x) { $math = $lib.import(testpkg.math) $y = (0) return($math.divcheck($x, $y)) }',
                },
            ),
        }

        async with self.getTestCore() as core:
            await core.addStormPkg(pkg)

            exc = None
            try:
                await core.nodes('$x = (10) $r = $lib.import(testpkg.ops).run($x)')
            except Exception as e:
                exc = e

            self.nn(exc)
            info = s_logging.excinfo(exc)

            storm = info.get('storm')
            self.nn(storm)

            # the failing expression is $a / $b inside testpkg.math, not the caller
            self.isin('$a', storm['text'])
            self.isin('$b', storm['text'])

            # function parameters a and b are captured as in-scope variables
            self.isin('$a', storm['vars'])
            self.isin('$b', storm['vars'])
            self.eq(storm['vars']['$a'], '10')
            self.eq(storm['vars']['$b'], '0')

    async def test_lib_logging_storm(self):

        # non-storm exceptions do not get a storm key
        try:
            raise s_exc.SynErr(mesg='nonstorm')
        except Exception as e:
            info = s_logging.excinfo(e)
            self.none(info.get('storm'))

        # storm exceptions include the failing expression text and in-scope variables
        async with self.getTestCore() as core:
            exc = None
            try:
                await core.nodes('$x = 5\n$z = ($x / 0)\n')
            except Exception as e:
                exc = e

            self.nn(exc)
            info = s_logging.excinfo(exc)

            storm = info.get('storm')
            self.nn(storm)
            self.isin('$x', storm['text'])
            self.isin('$x', storm['vars'])
